"""24h 级压测脚本（压缩时间跑批）。

用"带 usage 的假 LLM"（零真实成本）+ 真实检索源，把任务高速跑很多轮，
观测：DB 行数/文件大小增长、内存峰值、限流冷却、日志裁剪、成本统计与成本上限。
最后按小时速率外推 24h 量级并做断言。

用法：
    .venv/bin/python scripts/stress_test.py [--minutes 5] [--target 500] [--with-s2]
"""
import argparse
import asyncio
import json
import os
import resource
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import Orchestrator  # noqa: E402
from app.db import DB  # noqa: E402


class FakeLLM:
    """假模型：返回确定性 JSON，并上报模拟 usage 以便验证成本追踪/上限。"""

    def __init__(self, usage_per_call: dict | None = None,
                 price_in_per_m: float = 0.27, price_out_per_m: float = 1.10):
        self.usage_per_call = usage_per_call or {}
        self.price_in_per_m = price_in_per_m
        self.price_out_per_m = price_out_per_m

    @property
    def configured(self) -> bool:
        return True

    def estimate_cost(self, usage: dict) -> float:
        return (usage.get("prompt_tokens", 0) / 1e6 * self.price_in_per_m
                + usage.get("completion_tokens", 0) / 1e6 * self.price_out_per_m)

    def _usage(self):
        if not self.usage_per_call:
            return {}
        return {k: int(v) for k, v in self.usage_per_call.items()}

    async def chat(self, messages, **kwargs):
        content = messages[-1]["content"]
        if "检索策略" in content:
            return json.dumps({
                "en_terms": ["GNSS multipath mitigation", "RTK urban canyon NLOS",
                             "GNSS receiver testing"],
                "zh_terms": ["多路径抑制"],
                "subfields": ["multipath"],
                "year_from": None,
            }, ensure_ascii=False)
        if "相关性评审员" in content:
            import re
            idxs = re.findall(r"^(\d+)\. 《", content, re.M)
            return json.dumps({
                "items": [{"index": int(i), "relevant": True, "score": 0.8,
                           "category": "multipath"} for i in idxs]
            }, ensure_ascii=False)
        if "中文深读" in content:
            return json.dumps({
                "summary": "该论文研究GNSS多路径抑制方法，提出改进算法并通过实验验证了定位精度提升。",
                "methods": ["信号相关域分析", "实测验证"],
                "findings": ["多路径抑制显著提升定位精度"],
                "relevance": "可指导接收机多路径测试场景设计",
                "category": "multipath",
            }, ensure_ascii=False)
        if "新的英文检索 query" in content:
            return json.dumps({
                "queries": ["3D mapping aided GNSS NLOS", "multipath mitigation machine learning",
                            "GNSS receiver multipath field test", "urban GNSS deep learning",
                            "multipath error model simulation"]
            }, ensure_ascii=False)
        if "研究趋势与空白" in content:
            return ("## 研究趋势与热点\n- 趋势1\n\n## 研究空白与机会\n- 空白1\n\n"
                    "## 对 GNSS 测试设备厂商的启示\n- 启示1")
        return "OK"

    async def chat_full(self, messages, **kwargs):
        return await self.chat(messages, **kwargs), self._usage()

    async def chat_json_full(self, messages, **kwargs):
        return json.loads(await self.chat(messages, **kwargs)), self._usage()

    async def chat_json(self, messages, **kwargs):
        return json.loads(await self.chat(messages, **kwargs))


def current_peak_mb() -> float:
    """进程峰值内存（MB）。macOS ru_maxrss 单位是字节，Linux 是 KB。"""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024


def db_stats(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    try:
        counts = {}
        for t in ("tasks", "papers", "queries", "task_logs"):
            counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        logs_keep = con.execute(
            "SELECT COUNT(*) FROM (SELECT task_id FROM task_logs GROUP BY task_id "
            "HAVING COUNT(*) > 2000)").fetchone()[0]
        return {
            "rows": counts,
            "over_log_cap_tasks": logs_keep,
            "db_mb": round(os.path.getsize(db_path) / 1e6, 3),
        }
    finally:
        con.close()


async def phase_cap_test(db: DB):
    """阶段 A：成本上限保险丝验证（任务级配置，每次调用约 $0.000245）。"""
    print("\n[阶段 A] 成本上限验证…")
    task = await db.create_task(
        topic="成本上限测试", direction="", target_count=1000,
        time_limit_hours=1,
        config={"year_back": 3, "max_task_cost_usd": 0.002})
    orch = Orchestrator(db, llm_factory=lambda _s, _m=None: FakeLLM(
        usage_per_call={"prompt_tokens": 500, "completion_tokens": 100},
        price_in_per_m=0.27, price_out_per_m=1.10))
    await orch.start(task["id"])
    t0 = time.time()
    while time.time() - t0 < 120:
        await asyncio.sleep(1)
        t = await db.get_task(task["id"])
        if t["status"] in ("completed", "stopped", "error"):
            break
    t = await db.get_task(task["id"])
    cost = t.get("cost") or {}
    print(f"  状态={t['status']} | LLM 调用 {cost.get('calls', 0)} 次 | "
          f"估算成本 ${cost.get('est_cost_usd', 0):.4f}")
    assert t["status"] == "completed", f"成本上限任务未正常完成: {t['status']} {t.get('error')}"
    assert cost.get("calls", 0) > 0, "成本未被追踪"
    # 上限 0.002；保险丝是粗粒度安全阀：允许在途调用（打分批次+深读池并发）少量超支
    assert 0 < cost.get("est_cost_usd", 0) <= 0.006, \
        f"成本上限未生效或超支过多（${cost.get('est_cost_usd', 0):.4f}）"
    logs = await db.get_logs(task["id"], limit=500)
    assert any("成本上限" in l["message"] for l in logs), "未输出成本上限日志"
    print("  ✅ 成本追踪 + 上限保险丝正常")
    await orch.shutdown()
    return task["id"]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=4.0, help="压测时长（分钟）")
    ap.add_argument("--target", type=int, default=500, help="目标篇数（大值以进入持续扩展）")
    ap.add_argument("--with-s2", action="store_true", help="启用 Semantic Scholar（可能限流，测冷却）")
    args = ap.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="gnss_stress_")
    db_path = os.path.join(tmpdir, "stress.db")
    db = DB(db_path)
    await db.init()
    srcs = ["openalex", "arxiv", "crossref"] + (["semanticscholar"] if args.with_s2 else [])
    await db.set_settings({
        "api_base": "mock", "api_key": "", "model": "mock",
        "sources_enabled": json.dumps(srcs),
        "year_back": "5", "relevance_threshold": "0.6",
        "price_in_per_m": "0.27", "price_out_per_m": "1.10",
        "max_task_cost_usd": "0",
    })

    await phase_cap_test(db)

    print(f"\n[阶段 B] 压测运行 {args.minutes} 分钟（目标 {args.target} 篇，达标后持续扩展）…")
    task = await db.create_task(
        topic="RTK 接收机在城市峡谷环境下的多路径抑制研究进展",
        direction="重点关注测试方法", target_count=args.target,
        time_limit_hours=24, config={"year_back": 5, "relevance_threshold": 0.6})
    orch = Orchestrator(db, llm_factory=lambda _s, _m=None: FakeLLM(
        usage_per_call={"prompt_tokens": 800, "completion_tokens": 200},
        price_in_per_m=0.27, price_out_per_m=1.10))
    await orch.start(task["id"])

    t0 = time.time()
    deadline = t0 + args.minutes * 60
    samples = []
    while time.time() < deadline:
        await asyncio.sleep(10)
        t = await db.get_task(task["id"])
        stats = db_stats(db_path)
        peak_mb = current_peak_mb()
        samples.append({
            "t": round(time.time() - t0),
            "status": t["status"],
            "rounds": t["rounds"],
            "counters": t["counters"],
            "cost": t.get("cost") or {},
            **stats,
            "peak_mb": round(peak_mb, 1),
        })
        c = t["counters"]
        print(f"\r  [{samples[-1]['t']}s] 轮次 {t['rounds']} | 检索 {c.get('found', 0)} | "
              f"相关 {c.get('relevant', 0)} | 深读 {c.get('read', 0)} | "
              f"rows {stats['rows']} | DB {stats['db_mb']}MB | 峰值内存 {peak_mb:.0f}MB | "
              f"成本 ${(t.get('cost') or {}).get('est_cost_usd', 0):.4f}  ", end="", flush=True)

    print("\n[阶段 B] 停止任务，等待收尾…")
    await orch.stop(task["id"])
    for _ in range(60):
        t = await db.get_task(task["id"])
        if t["status"] in ("stopped", "completed", "error"):
            break
        await asyncio.sleep(2)
    t = await db.get_task(task["id"])
    final = db_stats(db_path)
    peak_mb = current_peak_mb()
    elapsed_h = (time.time() - t0) / 3600
    c = t["counters"]

    print("\n================ 压测结果 ================")
    print(f"任务状态：{t['status']}（{t.get('error') or '无错误'}）")
    print(f"运行 {round(time.time() - t0)}s = {elapsed_h:.3f}h，轮次 {t['rounds']}")
    print(f"检索 {c.get('found', 0)} → 相关 {c.get('relevant', 0)} → 深读 {c.get('read', 0)}")
    cost = t.get("cost") or {}
    print(f"LLM 调用 {cost.get('calls', 0)} 次，输入 {cost.get('in_tokens', 0):,}，"
          f"输出 {cost.get('out_tokens', 0):,}，估算 ${cost.get('est_cost_usd', 0):.4f}")
    print(f"DB 行数：{final['rows']}，DB 大小 {final['db_mb']}MB，峰值内存 {peak_mb:.0f}MB")
    hours = 24
    max_papers = max(int(args.target * 8), 200)  # 与编排器一致的检索总量上限

    # 论文总量受上限约束（有界系统，不做线性外推）
    papers_final = final["rows"]["papers"]
    db_at_cap_mb = final["db_mb"] * (max_papers / max(papers_final, 1))
    print(f"\n--- 24h 外推（论文总量有界） ---")
    print(f"论文总量：当前 {papers_final} 篇，受上限 {max_papers} 篇约束，24h 内不再增长")
    print(f"DB 大小：当前 {final['db_mb']}MB → 达到上限时约 {db_at_cap_mb:.0f}MB")
    print(f"LLM 调用/小时 ≈ {cost.get('calls', 0) / elapsed_h:.0f} → 24h ≈ "
          f"{cost.get('calls', 0) / elapsed_h * hours:,.0f} 次（随持续深读线性增长，受成本上限约束）")
    print(f"成本/小时 ≈ ${(cost.get('est_cost_usd', 0) / elapsed_h):.4f} → 24h ≈ "
          f"${cost.get('est_cost_usd', 0) / elapsed_h * hours:.2f}（受成本上限约束）")

    # 断言：长跑不失控
    assert t["status"] in ("stopped", "completed"), f"任务异常: {t['status']}"
    assert final["rows"]["task_logs"] <= 2100, "日志滚动未生效（超过 2000 上限）"
    assert papers_final <= max_papers + 500, \
        f"论文总量超过上限（{papers_final} > {max_papers}+500）——检索总量上限未生效"
    assert db_at_cap_mb < 200, f"论文达到上限时 DB 过大（{db_at_cap_mb:.0f}MB）"
    assert peak_mb < 1536, f"峰值内存异常（{peak_mb:.0f}MB > 1.5GB）"
    assert cost.get("calls", 0) > 0, "成本未追踪"
    print("\n🎉 压测全部通过：论文总量有界、DB 可控、内存稳定，日志滚动/成本追踪/上限均正常")

    await orch.shutdown()
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
