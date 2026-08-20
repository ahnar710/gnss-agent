"""深读员 Agent：对单篇论文生成中文结构化深读。"""
from ...llm.client import LLMError
from .base import Role

READ_PROMPT = (
    "你是 GNSS 领域研究助理（深读员）。请对以下论文做中文深读，输出 JSON：\n"
    "{{\n"
    '  "summary": "150~250 字中文客观摘要：研究问题、方法、主要结果",\n'
    '  "methods": ["方法要点，2~5 项"],\n'
    '  "findings": ["关键结论，2~4 项"],\n'
    '  "relevance": "该研究对 GNSS 测试/产品规划的价值，50~100 字",\n'
    '  "category": "子领域名（从固定列表选）"\n'
    "}}\n\n"
    "标题：{title}\n年份：{year}  来源：{venue}\n"
    "作者：{authors}\n"
    "摘要：{abstract}\n\n"
    "重要：只能依据以上给定信息总结，不得编造论文未提供的内容。"
)


class Reader(Role):
    name = "reader"
    label = "深读员"

    async def read(self, paper: dict) -> dict | None:
        """深读单篇论文；输出不合格时返回 None。
        用户上传的 PDF（source=upload）含全文，用更长片段做深读。"""
        if paper.get("source") == "upload":
            abstract = (paper.get("abstract") or "（无全文）")[:6000]
        else:
            abstract = (paper.get("abstract") or "（无摘要）")[:1200]
        try:
            data = await self._json(
                [{"role": "user", "content": READ_PROMPT.format(
                    title=paper["title"],
                    year=paper.get("year") or "未知",
                    venue=paper.get("venue") or "未知",
                    authors=", ".join((paper.get("authors") or [])[:6]),
                    abstract=abstract)}],
                max_tokens=1500)
        except LLMError:
            return None
        if not isinstance(data, dict) or not data.get("summary"):
            return None
        return data
