"""主编 Agent（质控）：批量核验深读摘要是否忠实于原文，防幻觉。

对"已深读"论文做抽查式复核：若摘要与原文摘要明显不符（编造/张冠李戴/夸大），
返回需要重读的论文 id 列表，协调器将其打回深读队列。
"""
from ...llm.client import LLMError
from .base import Role

VERIFY_PROMPT = (
    "你是 GNSS 文献主编（质控员）。以下是若干篇论文：【英文标题+原始摘要片段】与对应的"
    "【中文深读摘要】。请逐篇判断中文摘要是否基于原文客观总结——没有编造事实、没有张冠李戴、"
    "没有夸大结论。\n\n"
    "{papers}\n\n"
    "输出 JSON：{{\"items\": [{{\"index\": 0, \"ok\": true, \"note\": \"通过\"}}]}}，"
    "index 对应论文编号。仅当明显不符时 ok 为 false，note 用一句话说明。"
)

BATCH_SIZE = 15


class Editor(Role):
    name = "editor"
    label = "主编(质控)"

    async def verify_batch(self, papers: list) -> list[int]:
        """返回需要重读的论文 id 列表；调用失败返回 []（不阻塞）。"""
        if not papers:
            return []
        lines = []
        for idx, p in enumerate(papers):
            abstract = (p.get("abstract") or "")[:300]
            summary = (p.get("summary") or "")[:250]
            lines.append(
                f"{idx}. 标题：{p['title']}\n   原文摘要：{abstract}\n"
                f"   中文深读：{summary}")
        try:
            data = await self._json(
                [{"role": "user", "content": VERIFY_PROMPT.format(
                    papers="\n\n".join(lines))}],
                max_tokens=1500)
        except LLMError:
            return []
        if not isinstance(data, dict):
            return []
        items = data.get("items")
        if not isinstance(items, list):
            return []
        flagged = []
        for it in items:
            try:
                idx = int(it.get("index"))
                if not it.get("ok"):
                    flagged.append(papers[idx]["id"])
            except (TypeError, ValueError, IndexError, KeyError):
                continue
        return flagged
