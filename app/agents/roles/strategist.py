"""策略官 Agent：主题解析 + 检索角度扩展。"""
from ...config import GNSS_SUBFIELDS
from ...domain.terms import SUBFIELDS
from ...llm.client import LLMError  # noqa: F401  (re-export 便于调用方捕获)
from .base import Role

SUBFIELDS_TEXT = ", ".join(GNSS_SUBFIELDS)

PARSE_PROMPT = (
    "你是一名 GNSS（全球导航卫星系统）领域的资深文献检索专家（策略官）。"
    "用户（GNSS 测试厂商产品经理）提出以下文献调研主题，请将其解析为可执行的检索策略。\n\n"
    "调研主题：{topic}\n补充说明：{direction}\n\n"
    "输出 JSON（不要输出任何其他内容）：\n"
    "{{\n"
    '  "en_terms": ["英文检索关键词，6~12 个，覆盖核心概念、同义词与技术变体"],\n'
    '  "zh_terms": ["中文检索关键词，3~8 个"],\n'
    '  "subfields": ["命中的子领域，从这些中选：' + SUBFIELDS_TEXT + '；未命中给空数组"],\n'
    '  "year_from": 建议的检索起始年份（数字），或 null（默认近十年）\n'
    "}}"
)

EXPAND_PROMPT = (
    "你是 GNSS 领域文献检索专家（策略官）。调研主题：{topic}\n"
    "目前已获得 {n} 篇相关文献，最相关的标题：\n{titles}\n\n"
    "请给出 5 个新的英文检索 query，从不同角度挖掘该主题尚未覆盖的文献"
    "（例如：特定方法、特定场景、技术组合、survey/review 类文献）。\n"
    '输出 JSON：{{"queries": ["...", "..."]}}'
)


class Strategist(Role):
    name = "strategist"
    label = "策略官"

    async def parse(self, topic: str, direction: str) -> dict:
        """主题 → 检索策略。失败返回空 dict（调用方兜底）。"""
        try:
            data = await self._json(
                [{"role": "user", "content": PARSE_PROMPT.format(
                    topic=topic, direction=direction or "（无）")}],
                max_tokens=1200)
        except LLMError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            "en_terms": [str(t) for t in (data.get("en_terms") or [])][:15],
            "zh_terms": [str(t) for t in (data.get("zh_terms") or [])][:10],
            "subfields": [s for s in (data.get("subfields") or []) if s in SUBFIELDS],
            "year_from": data.get("year_from"),
        }

    async def expand(self, topic: str, titles: list[str]) -> list[str]:
        """基于已读文献提出新的检索角度。"""
        try:
            data = await self._json(
                [{"role": "user", "content": EXPAND_PROMPT.format(
                    topic=topic, n=len(titles),
                    titles="\n".join(f"- {t}" for t in titles))}],
                max_tokens=600)
        except LLMError:
            return []
        if not isinstance(data, dict):
            return []
        return [str(q).strip() for q in (data.get("queries") or []) if str(q).strip()]
