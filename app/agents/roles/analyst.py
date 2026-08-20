"""分析师 Agent：基于已深读文献撰写研究趋势与空白分析。"""
from ...llm.client import LLMError
from .base import Role

ANALYZE_PROMPT = (
    "你是 GNSS 行业技术分析师。以下是 {n} 篇文献的中文深读摘要（按子领域分组）：\n\n"
    "{block}\n\n"
    "请撰写「研究趋势与空白分析」，输出 Markdown：\n"
    "## 研究趋势与热点\n（3~5 点，每点一段）\n"
    "## 研究空白与机会\n（3~5 点）\n"
    "## 对 GNSS 测试设备厂商的启示\n（3~5 点，站在产品规划视角，具体可落地）"
)


class Analyst(Role):
    name = "analyst"
    label = "分析师"

    async def analyze(self, n: int, grouped_block: str) -> str:
        """返回 Markdown 分析文本；失败返回降级文案。"""
        try:
            text = await self._text(
                [{"role": "user", "content": ANALYZE_PROMPT.format(
                    n=n, block=grouped_block)}],
                max_tokens=1800, temperature=0.4)
            return (text or "").strip() or "（模型未返回分析内容）\n"
        except LLMError:
            return ("（LLM 分析生成失败，请稍后重新生成报告。"
                    "可参考上方逐篇深读内容自行归纳。）\n")
