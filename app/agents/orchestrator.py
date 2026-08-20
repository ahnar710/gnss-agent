"""固定工作流协调器（多 Agent 版）：解析 → 多源检索 → 打分 → 并行深读 → 扩展 → 报告。

- 每个任务一个 asyncio 协程；重启后自动恢复 status='running'/'stopping' 的任务
- 角色流水线：策略官 / 评审员 / 深读员池 / 分析师 / 主编(质控)，通过 SQLite 黑板协作
- 所有状态落 SQLite，步骤幂等（queries 表 + papers 状态）
- 达标后进入"过载模式"持续扩展，直到用户停止 / 时间上限 / 成本上限
"""
import asyncio
import json
import logging
from datetime import datetime

from ..db import DB
from ..domain.terms import SUBFIELDS
from ..llm.client import LLMClient
from ..sources import Source, SourceError, SourceRateLimited, build_sources
from .pool import ReaderPool
from .roles import RoleSet

logger = logging.getLogger("orchestrator")

DEFAULT_SOURCES = ["openalex", "arxiv", "semanticscholar", "crossref"]
QUERIES_PER_ROUND = 3
SCORE_BATCH = 10
MAX_CONCURRENT_TASKS = 3


class Orchestrator:
    # 各任务已质控到哪篇（进程内状态；恢复任务后从头再查一次也无妨）
    _qc_checked: dict[str, int] = {}

    def __init__(self, db: DB, llm_factory=None):
        self.db = db
        self._tasks: dict[str, asyncio.Task] = {}
        self._stop_flags: dict[str, asyncio.Event] = {}
        self._sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        self._llm_sem = asyncio.Semaphore(2)  # 打分/扩展等突发调用限流
        self._source_cooldown: dict[str, float] = {}  # 源名 -> 冷却截止时间戳
        # 可注入工厂（测试/演示用）；默认从设置构建
        # 工厂契约：llm_factory(settings, model_override|None) -> LLM 实例
        self._llm_factory = llm_factory or self._default_llm

    @staticmethod
    def _default_llm(settings: dict, model_override: str | None = None) -> LLMClient:
        return LLMClient(
            settings.get("api_base", ""), settings.get("api_key", ""),
            model_override or settings.get("model", ""),
            price_in_per_m=float(settings.get("price_in_per_m") or 0.27),
            price_out_per_m=float(settings.get("price_out_per_m") or 1.10),
        )

    # ---------------- 成本追踪 ----------------
    async def _track_cost(self, task_id: str, llm, usage: dict):
        if usage:
            await self.db.add_cost(task_id,
                                   usage.get("prompt_tokens", 0),
                                   usage.get("completion_tokens", 0),
                                   llm.estimate_cost(usage))
        else:
            # 模型未返回 usage（如演示模式）时仍计入调用次数
            await self.db.add_cost(task_id)

    # ---------------- 公共入口 ----------------
    async def start(self, task_id: str):
        """启动（或恢复）一个任务。若上次是 'stopping'，恢复后保持停止请求。"""
        if task_id in self._tasks and not self._tasks[task_id].done():
            return
        task = await self.db.get_task(task_id)
        ev = asyncio.Event()
        if task and task["status"] == "stopping":
            ev.set()
        self._stop_flags[task_id] = ev
        self._tasks[task_id] = asyncio.create_task(self._run(task_id))

    async def stop(self, task_id: str):
        """请求优雅停止：当前步骤完成后生成最终报告。"""
        if task_id in self._stop_flags:
            self._stop_flags[task_id].set()
        else:
            self._stop_flags[task_id] = asyncio.Event()
            self._stop_flags[task_id].set()

    async def resume_running(self):
        """应用启动时恢复所有未完成任务。"""
        for t in await self.db.list_tasks():
            if t["status"] in ("running", "stopping"):
                await self.db.add_log(t["id"], "应用重启，自动恢复任务", "warn")
                await self.start(t["id"])

    async def shutdown(self):
        for tid, t in list(self._tasks.items()):
            self._stop_flags.setdefault(tid, asyncio.Event()).set()
            t.cancel()

    # ---------------- 主循环 ----------------
    async def _run(self, task_id: str):
        async with self._sem:
            try:
                await self._workflow(task_id)
            except asyncio.CancelledError:
                await self.db.update_task(task_id, status="stopping")
                await self.db.add_log(task_id, "任务被取消，状态置为 stopping", "warn")
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception("task %s crashed", task_id)
                await self.db.update_task(task_id, status="error", error=str(e)[:500])
                await self.db.add_log(task_id, f"任务异常终止: {e}", "error")
            finally:
                self._tasks.pop(task_id, None)

    async def _workflow(self, task_id: str):
        task = await self.db.get_task(task_id)
        if not task:
            return
        settings = await self.db.get_settings()
        cfg = task.get("config") or {}  # get_task 已解析 JSON
        target = int(task.get("target_count") or 100)
        time_limit_h = float(task.get("time_limit_hours") or 24)
        year_to = datetime.now().year
        year_back = int(cfg.get("year_back") or settings.get("year_back") or 10)
        year_from = int(cfg.get("year_from") or (year_to - year_back))
        threshold = float(cfg.get("relevance_threshold")
                          or settings.get("relevance_threshold") or 0.6)
        enabled = json.loads(settings.get("sources_enabled") or json.dumps(DEFAULT_SOURCES))
        sources = build_sources(enabled, settings.get("mailto", ""))
        # 成本上限：任务级配置优先，其次全局设置；0=不限
        cost_cap = float(cfg.get("max_task_cost_usd")
                         or settings.get("max_task_cost_usd") or 0)
        reader_pool_size = int(settings.get("reader_pool_size") or 3)
        qc_enabled = str(settings.get("qc_enabled") or "1") == "1"
        stop_ev = self._stop_flags.setdefault(task_id, asyncio.Event())

        # 多 Agent 角色集（每角色独立模型，共享成本追踪）
        async def usage_recorder(llm, usage):
            await self._track_cost(task_id, llm, usage)

        roles = RoleSet(settings, self._llm_factory, usage_recorder)

        if not roles.strategist.configured:
            await self.db.update_task(task_id, status="error",
                                      error="未配置大模型，请在设置页填写 API 信息")
            await self.db.add_log(task_id, "未配置大模型，任务无法开始", "error")
            return

        topic = task["topic"]
        direction = task.get("direction") or ""
        started = datetime.fromisoformat(task["started_at"])
        await self.db.add_log(
            task_id, f"任务启动：{topic}（目标 {target} 篇，上限 {time_limit_h} 小时，"
                     f"深读并发 {reader_pool_size}）")

        # ---------- 阶段 1：策略官解析主题 ----------
        strategy = await roles.strategist.parse(topic, direction)
        pending_queries: list[str] = await self._initial_queries(task_id, strategy)
        if not pending_queries:
            # 兜底：直接把主题本身作为检索式
            pending_queries = [topic]
        await self.db.add_log(
            task_id,
            f"策略官解析完成：英文词 {len(strategy.get('en_terms', []))} 个，"
            f"中文词 {len(strategy.get('zh_terms', []))} 个，"
            f"子领域 {strategy.get('subfields') or []}")

        # ---------- 阶段 4：启动深读员并行池 ----------
        pool = ReaderPool(self.db, roles.reader, task_id, size=reader_pool_size,
                          record_usage=usage_recorder, cost_cap=cost_cap)
        await pool.start()

        rounds = int(task.get("rounds") or 0)
        last_report_reads = -1
        last_qc_id = 0
        target_reported = False
        idle_streak = 0
        stop_reason: str | None = None
        # 论文总量上限：防止 24h 过载模式无限灌论文导致 DB 膨胀（默认目标×8，下限 200）
        max_papers = max(int(target * 8), 200)
        search_paused_logged = False

        # ---------- 主循环：不点停止不停 ----------
        while not stop_ev.is_set():
            # 时间上限检查
            elapsed_h = (datetime.now() - started).total_seconds() / 3600.0
            if elapsed_h >= time_limit_h:
                await self.db.add_log(task_id, f"达到时间上限（{time_limit_h} 小时），结束运行")
                stop_reason = "时间上限"
                break

            # 成本上限检查（进入本轮任何 LLM 调用前先查，配合深读池自查，缩小超支窗口）
            t_now = await self.db.get_task(task_id)
            cost_now = float((t_now.get("cost") or {}).get("est_cost_usd", 0.0))
            if cost_cap > 0 and cost_now >= cost_cap:
                await self.db.add_log(
                    task_id, f"已达到成本上限 ${cost_cap:.2f}（已花费 ${cost_now:.2f}），"
                             "结束运行并生成最终报告", "warn")
                stop_reason = "成本上限"
                break

            counters_now = t_now["counters"]
            intake_full = counters_now.get("found", 0) >= max_papers

            # 阶段 2：多源检索（论文总量达到上限后暂停检索，专注深读积压）
            if pending_queries and not intake_full:
                batch = pending_queries[:QUERIES_PER_ROUND]
                pending_queries = pending_queries[QUERIES_PER_ROUND:]
                found = await self._search_queries(task_id, batch, sources, year_from, year_to)
                if found:
                    idle_streak = 0
                else:
                    idle_streak += 1
            elif pending_queries and intake_full:
                if not search_paused_logged:
                    await self.db.add_log(
                        task_id, f"已检索 {counters_now.get('found', 0)} 篇，达到论文总量上限 "
                                 f"({max_papers} 篇)，暂停检索，专注深读与打分", "warn")
                    search_paused_logged = True
                pending_queries = []
                idle_streak += 1
            else:
                idle_streak += 1

            # 阶段 3：评审员打分（深读池并行运行，不阻塞）
            if not stop_ev.is_set():
                await self._score_pending(task_id, roles, topic, direction, threshold)

            t_now = await self.db.get_task(task_id)
            counters = t_now["counters"]
            # 达标通知（一次）
            if not target_reported and counters["read"] >= target:
                target_reported = True
                await self.db.add_log(
                    task_id, f"已深读 {counters['read']} 篇，达到目标 {target} 篇；"
                             "进入持续扩展模式（用户不点停止则不结束）", "success")

            # 报告刷新 + 主编质控（每新增 10 篇深读或每 5 轮）
            if counters["read"] - last_report_reads >= 10 or rounds % 5 == 4:
                await self._generate_report(task_id, roles)
                last_report_reads = counters["read"]
            if qc_enabled and counters["read"] - self._qc_checked.get(task_id, 0) >= 10:
                await self._qc_check(task_id, roles)

            # 阶段 5：策略官扩展检索（新关键词 / 引用网络）——论文总量达标后不再扩源
            if not pending_queries and not intake_full:
                new_q = await self._expand_queries(task_id, roles, topic)
                if new_q:
                    pending_queries.extend(new_q)
                    idle_streak = 0
                else:
                    mined = await self._citation_mining(task_id, sources)
                    if mined:
                        idle_streak = 0
                    elif idle_streak >= 3:
                        await self.db.add_log(task_id, "暂无可扩展的检索角度，60 秒后重试", "warn")
                        await asyncio.sleep(60)
                        idle_streak = 0

            rounds += 1
            await self.db.update_task(task_id, rounds=rounds)
            if rounds % 20 == 0:
                await self.db.prune_logs(task_id)  # 日志滚动，防磁盘膨胀
            if rounds % 50 == 0:
                await self.db.checkpoint()  # WAL 压缩，保持 DB 文件紧凑
            await asyncio.sleep(0.2)

        # ---------- 收尾：停池 → 最终报告 ----------
        await pool.stop()
        reason = stop_reason or ("用户停止" if stop_ev.is_set() else "时间上限")
        await self.db.add_log(task_id, f"结束运行（{reason}），生成最终报告…")
        await self._generate_report(task_id, roles)
        counters = (await self.db.get_task(task_id))["counters"]
        cost = (await self.db.get_task(task_id)).get("cost") or {}
        final_status = "stopped" if (stop_reason is None and stop_ev.is_set()) else "completed"
        await self.db.update_task(task_id, status=final_status,
                                  stopped_at=datetime.now().isoformat(timespec="seconds"))
        await self.db.add_log(
            task_id,
            f"任务完成（{final_status}）：检索 {counters['found']} 篇，"
            f"相关 {counters['relevant']} 篇，深读 {counters['read']} 篇，"
            f"LLM 调用 {cost.get('calls', 0)} 次，估算成本 ${cost.get('est_cost_usd', 0):.3f}", "success")

    # ---------------- 阶段实现（路由到角色） ----------------
    async def _initial_queries(self, task_id: str, strategy: dict) -> list[str]:
        """由策略生成初始检索 query（含领域词库补充）。"""
        queries: list[str] = []
        for t in strategy.get("en_terms", []):
            queries.append(t)
        for t in strategy.get("zh_terms", []):
            queries.append(t)
        for sf in strategy.get("subfields", []):
            info = SUBFIELDS.get(sf)
            if info:
                queries.append(info["phrase"])
        # 去重 + 过滤已检索
        seen = set()
        out = []
        for q in queries:
            q = q.strip()
            if not q or q.lower() in seen:
                continue
            seen.add(q.lower())
            if await self.db.has_query_text(task_id, q):
                continue
            out.append(q)
        return out[:12]

    async def _search_queries(self, task_id: str, queries: list[str],
                              sources: list[Source], year_from: int, year_to: int) -> int:
        """对一批 query × 全部源并发检索（多源并行），返回新增论文数。"""
        total_new = 0
        results: dict[str, list[dict]] = {q: [] for q in queries}
        sem = asyncio.Semaphore(6)
        now = datetime.now().timestamp()

        async def one(q: str, src: Source):
            if self._source_cooldown.get(src.name, 0) > now:
                return  # 限流冷却中，跳过
            try:
                async with sem:
                    papers = await src.search(q, year_from, year_to, limit=30)
                results[q].extend(papers)
            except SourceRateLimited as e:
                self._source_cooldown[src.name] = now + 300
                await self.db.add_log(
                    task_id, f"[{src.label}] 限流，暂停该源 5 分钟: {e}", "warn")
            except SourceError as e:
                await self.db.add_log(task_id, f"[{src.label}] {q} 检索失败: {e}", "warn")
            except Exception as e:  # noqa: BLE001
                logger.exception("search error")
                await self.db.add_log(task_id, f"[{src.label}] {q} 异常: {e}", "warn")
            await self.db.add_query(task_id, q, src.name)

        await asyncio.gather(*(one(q, src) for q in queries for src in sources))
        for q, papers in results.items():
            if not papers:
                continue
            new = await self.db.insert_papers(task_id, papers)
            total_new += new
            if new:
                await self.db.add_log(
                    task_id, f"检索「{q}」新增 {new} 篇（去重后），"
                             f"当前累计 {await self.db.count_papers(task_id)} 篇")
        # 更新计数
        counters = (await self.db.get_task(task_id))["counters"]
        counters["found"] = await self.db.count_papers(task_id)
        counters["queries"] = len(await self.db.list_queries(task_id))
        await self.db.update_task(task_id, counters=counters)
        return total_new

    async def _score_pending(self, task_id: str, roles: RoleSet, topic: str,
                             direction: str, threshold: float):
        """评审员批量打分未评分论文，标记相关/不相关。"""
        pending = await self.db.pending_papers(task_id, limit=50)
        if not pending:
            return
        scored_ok = 0
        for i in range(0, len(pending), SCORE_BATCH):
            batch = pending[i:i + SCORE_BATCH]
            try:
                async with self._llm_sem:
                    items = await roles.reviewer.score(topic, direction, batch)
            except Exception as e:  # noqa: BLE001
                await self.db.add_log(task_id, f"评审员打分异常（稍后重试）: {e}", "warn")
                return
            if not items:
                await self.db.add_log(task_id, "评审员打分输出异常，跳过本批", "warn")
                return
            for it in items:
                try:
                    idx = int(it.get("index"))
                    p = batch[idx]
                except (TypeError, ValueError, IndexError, KeyError):
                    continue
                relevant = bool(it.get("relevant"))
                score = float(it.get("score") or 0)
                cat = it.get("category") or "other"
                if cat not in SUBFIELDS:
                    cat = "other"
                if relevant and score >= threshold:
                    await self.db.update_paper(p["id"], status="relevant",
                                               relevance=score, category=cat)
                    scored_ok += 1
                else:
                    await self.db.update_paper(p["id"], status="scored",
                                               relevance=score, category=cat)
        if scored_ok:
            counters = (await self.db.get_task(task_id))["counters"]
            counters["relevant"] = await self.db.count_papers(task_id, status="relevant")
            await self.db.update_task(task_id, counters=counters)
            await self.db.add_log(
                task_id, f"本批打分：新增相关 {scored_ok} 篇，累计相关 {counters['relevant']} 篇")

    async def _expand_queries(self, task_id: str, roles: RoleSet, topic: str) -> list[str]:
        """策略官基于已读文献提出新的检索角度。"""
        read = await self.db.read_papers(task_id)
        titles = [r["title"][:100] for r in read[:15]]
        try:
            async with self._llm_sem:
                queries = await roles.strategist.expand(topic, titles)
        except Exception as e:  # noqa: BLE001
            await self.db.add_log(task_id, f"策略官扩展检索异常: {e}", "warn")
            return []
        new = []
        seen = set()
        for q in queries:
            q = str(q).strip()
            if not q or q.lower() in seen:
                continue
            seen.add(q.lower())
            if await self.db.has_query_text(task_id, q):
                continue
            new.append(q)
        if new:
            await self.db.add_log(task_id, f"策略官扩展：提出 {len(new)} 个新角度")
        return new[:5]

    async def _qc_check(self, task_id: str, roles: RoleSet):
        """主编质控：核验新近深读摘要的忠实性，不符打回重读。"""
        try:
            papers = await self.db.recent_read_papers(task_id,
                                                      after_id=self._qc_checked.get(task_id, 0),
                                                      limit=15)
            if not papers:
                return
            flagged = await roles.editor.verify_batch(papers)
            self._qc_checked[task_id] = max(p["id"] for p in papers)
            for pid in flagged:
                extras = next((p.get("extras") or {} for p in papers if p["id"] == pid), {})
                extras = dict(extras)
                extras["qc"] = 1
                await self.db.update_paper(pid, status="relevant", extras=extras)
            if flagged:
                await self.db.add_log(
                    task_id, f"主编质控：复核 {len(papers)} 篇，{len(flagged)} 篇不符已打回重读", "warn")
            else:
                await self.db.add_log(task_id, f"主编质控：复核 {len(papers)} 篇，全部通过")
        except Exception as e:  # noqa: BLE001
            logger.exception("qc check failed")
            await self.db.add_log(task_id, f"主编质控异常: {e}", "warn")

    async def _citation_mining(self, task_id: str, sources: list[Source]) -> int:
        """从已存论文的引用网络挖掘新文献（OpenAlex referenced_works）。"""
        openalex = next((s for s in sources if s.name == "openalex"), None)
        if openalex is None:
            return 0
        rows = await self.db.get_papers(task_id, limit=10000)
        ref_ids: list[str] = []
        for r in rows:
            for rid in (r.get("extras") or {}).get("_referenced", []) or []:
                if rid not in ref_ids:
                    ref_ids.append(rid)
        if not ref_ids:
            return 0
        try:
            mined = await openalex.fetch_works_by_ids(ref_ids, limit=60)
        except SourceError as e:
            await self.db.add_log(task_id, f"引用网络挖掘失败: {e}", "warn")
            return 0
        new = await self.db.insert_papers(task_id, mined)
        if new:
            await self.db.add_log(task_id, f"引用网络挖掘：新增 {new} 篇")
            counters = (await self.db.get_task(task_id))["counters"]
            counters["found"] = await self.db.count_papers(task_id)
            await self.db.update_task(task_id, counters=counters)
        return new

    # ---------------- 报告 ----------------
    async def _generate_report(self, task_id: str, roles: RoleSet):
        from .report import generate_report
        try:
            await generate_report(self.db, task_id, roles.analyst)
        except Exception as e:  # noqa: BLE001
            logger.exception("report failed")
            await self.db.add_log(task_id, f"报告生成失败: {e}", "error")
