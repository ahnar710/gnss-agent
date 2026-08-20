"""深读员 Worker 池：N 个并发深读 Worker，从 SQLite 黑板原子认领论文。

- 认领：db.claim_next_relevant（BEGIN IMMEDIATE + 优先级排序 + 置 reading 状态）
- 失败：释放回队列（attempts+1），重试超限标记 failed；崩溃遗留的 reading 由 reset 恢复
- 成本：每次深读的 usage 通过 record_usage 上报
"""
import asyncio
import logging

logger = logging.getLogger("pool")


class ReaderPool:
    def __init__(self, db, reader, task_id: str, size: int = 3,
                 record_usage=None, llm_sem=None, cost_cap: float = 0.0):
        self.db = db
        self.reader = reader
        self.task_id = task_id
        self.size = max(1, min(int(size or 3), 6))
        self.record_usage = record_usage  # async (llm, usage) -> None
        self.llm_sem = llm_sem
        self.cost_cap = float(cost_cap or 0)
        self._stop = asyncio.Event()
        self._workers: list[asyncio.Task] = []
        self._recent = 0

    async def start(self):
        # 恢复上次崩溃可能遗留的 reading 论文
        await self.db.reset_reading(self.task_id)
        for _ in range(self.size):
            self._workers.append(asyncio.create_task(self._worker()))

    async def stop(self, grace: float = 10.0):
        """优雅停池：先让 worker 完成当前论文，超时才强制取消。"""
        self._stop.set()
        if not self._workers:
            return
        done, pending = await asyncio.wait(self._workers, timeout=grace)
        for w in pending:
            w.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._workers = []

    async def _worker(self):
        while not self._stop.is_set():
            # 成本上限自查：达到上限立即停止深读（防止检查间隙超支）
            if self.cost_cap > 0:
                cost = await self._current_cost()
                if cost >= self.cost_cap:
                    return
            paper = await self.db.claim_next_relevant(self.task_id)
            if paper is None:
                await asyncio.sleep(2)
                continue
            try:
                if self.llm_sem:
                    async with self.llm_sem:
                        data = await self.reader.read(paper)
                else:
                    data = await self.reader.read(paper)
            except asyncio.CancelledError:
                # 被取消：若论文仍未被处理完，释放回队列
                await self.db.release_if_reading(paper["id"])
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception("reader worker error")
                await self._release_or_fail(paper, str(e))
                continue
            if not data:
                await self._release_or_fail(paper, "输出不合格")
                continue
            kp = {"methods": data.get("methods") or [],
                  "findings": data.get("findings") or [],
                  "relevance": str(data.get("relevance") or "")[:500]}
            await self.db.update_paper(
                paper["id"], status="read",
                category=data.get("category") or paper.get("category") or "other",
                summary=str(data.get("summary"))[:2000], key_points=kp)
            await self.db.inc_counter(self.task_id, "read")
            self._recent += 1
            await self.db.add_log(
                self.task_id, f"深读完成 #{self._recent}：{paper['title'][:60]}…")

    async def _current_cost(self) -> float:
        row = await self.db.get_task(self.task_id)
        return float((row.get("cost") or {}).get("est_cost_usd", 0.0)) if row else 0.0

    async def _release_or_fail(self, paper: dict, why: str):
        attempts = int((paper.get("extras") or {}).get("attempts", 0))
        if attempts >= 3:
            await self.db.mark_failed(paper["id"])
        else:
            await self.db.release_paper(paper["id"])
