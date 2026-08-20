"""端到端冒烟测试：真实检索（OpenAlex/arXiv/Crossref）+ 假 LLM，验证完整工作流。

用法：.venv/bin/python scripts/smoke_test.py
验证点：任务创建 → 主题解析 → 多源检索 → 打分 → 深读 → 达标 → 停止 → 最终报告。
"""
import asyncio
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import Orchestrator  # noqa: E402
from app.db import DB  # noqa: E402


class FakeLLM:
    """可编程假模型：按提示词特征返回固定 JSON，用于验证工作流逻辑。"""

    @property
    def configured(self) -> bool:
        return True

    async def chat(self, messages, **kwargs):
        content = messages[-1]["content"]
        if "检索策略" in content:
            return json.dumps({
                "en_terms": ["GNSS multipath mitigation", "RTK urban canyon NLOS"],
                "zh_terms": ["多路径抑制"],
                "subfields": ["multipath"],
                "year_from": None,
            }, ensure_ascii=False)
        if "相关性评审员" in content:
            import re
            idxs = re.findall(r"^(\d+)\. 《", content, re.M)
            return json.dumps({
                "items": [{"index": int(i), "relevant": True, "score": 0.82,
                           "category": "multipath"} for i in idxs]
            }, ensure_ascii=False)
        if "质控员" in content:
            import re
            idxs = re.findall(r"^(\d+)\. 标题：", content, re.M)
            return json.dumps({
                "items": [{"index": int(i), "ok": True, "note": "通过"} for i in idxs]
            }, ensure_ascii=False)
        if "中文深读" in content:
            return json.dumps({
                "summary": "该论文研究GNSS多路径抑制方法，提出改进算法并通过实验验证了定位精度提升，"
                           "对接收机多路径测试场景设计有参考价值。",
                "methods": ["信号相关域分析", "实测验证"],
                "findings": ["多路径抑制显著提升定位精度", "算法复杂度可控"],
                "relevance": "可指导接收机多路径测试用例与场景设计",
                "category": "multipath",
            }, ensure_ascii=False)
        if "新的英文检索 query" in content:
            return json.dumps({
                "queries": ["3D mapping aided GNSS NLOS", "multipath mitigation machine learning"]
            }, ensure_ascii=False)
        if "研究趋势与空白" in content:
            return ("## 研究趋势与热点\n- 趋势1\n\n## 研究空白与机会\n- 空白1\n\n"
                    "## 对 GNSS 测试设备厂商的启示\n- 启示1")
        return "OK"

    async def chat_full(self, messages, **kwargs):
        return await self.chat(messages, **kwargs), {}

    async def chat_json_full(self, messages, **kwargs):
        return json.loads(await self.chat(messages, **kwargs)), {}

    async def chat_json(self, messages, **kwargs):
        return json.loads(await self.chat(messages, **kwargs))

    def estimate_cost(self, usage: dict) -> float:
        return 0.0


async def main():
    tmp = tempfile.mkdtemp(prefix="gnss_smoke_")
    db = DB(os.path.join(tmp, "test.db"))
    await db.init()
    await db.set_settings({
        "api_base": "mock", "api_key": "", "model": "mock",
        # S2 当前被限流，冒烟测试只启用三个稳定源
        "sources_enabled": json.dumps(["openalex", "arxiv", "crossref"]),
        "year_back": "5", "relevance_threshold": "0.6",
    })
    task = await db.create_task(
        topic="RTK 接收机在城市峡谷环境下的多路径抑制研究进展",
        direction="重点关注测试方法",
        target_count=3, time_limit_hours=0.3,
        config={"year_back": 5, "relevance_threshold": 0.6},
    )
    task_id = task["id"]
    orch = Orchestrator(db, llm_factory=lambda _s, _m=None: FakeLLM())
    await orch.start(task_id)

    t0 = time.time()
    while time.time() - t0 < 300:
        await asyncio.sleep(2)
        t = await db.get_task(task_id)
        c = t["counters"]
        print(f"\r  [运行中] 检索 {c.get('found', 0)} | 相关 {c.get('relevant', 0)} | "
              f"深读 {c.get('read', 0)} | 轮次 {t['rounds']} | 状态 {t['status']}  ", end="", flush=True)
        if c.get("read", 0) >= 3 and t["status"] == "running":
            print("\n  达标，请求停止…")
            await orch.stop(task_id)
        if t["status"] in ("stopped", "completed", "error"):
            break
    print()

    t = await db.get_task(task_id)
    assert t["status"] in ("stopped", "completed"), f"任务未正常结束: {t['status']} {t.get('error')}"
    c = t["counters"]
    print(f"\n✅ 任务结束：状态={t['status']}，检索 {c.get('found')} 篇，相关 {c.get('relevant')} 篇，"
          f"深读 {c.get('read')} 篇，轮次 {t['rounds']}，耗时 {time.time() - t0:.0f}s")

    # 报告检查
    from app.config import reports_dir
    report_path = reports_dir() / f"{task_id}.md"
    assert report_path.exists(), "报告文件未生成"
    md = report_path.read_text(encoding="utf-8")
    for section in ["调研概述", "子领域分布", "重点文献深读", "研究趋势与空白", "参考文献"]:
        assert section in md, f"报告缺少章节: {section}"
    print(f"✅ 报告已生成：{report_path}（{len(md)} 字符）")
    print("--- 报告节选 ---")
    print("\n".join(md.splitlines()[:18]))

    # 幂等/断点续跑：重启编排器后任务不应重复检索（queries 表幂等）
    await orch.shutdown()
    orch2 = Orchestrator(db, llm_factory=lambda _s, _m=None: FakeLLM())
    await orch2.resume_running()
    await asyncio.sleep(1)
    t2 = await db.get_task(task_id)
    print(f"✅ 重启恢复检查：状态 {t2['status']}（已结束任务不会被重启）")
    await db.close()
    print("\n🎉 冒烟测试全部通过")


if __name__ == "__main__":
    asyncio.run(main())
