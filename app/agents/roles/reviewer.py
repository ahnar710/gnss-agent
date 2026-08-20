"""评审员 Agent：批量相关性打分与子领域分类。"""
from ...llm.client import LLMError
from .base import Role

SCORE_PROMPT = (
    "你是 GNSS 领域文献相关性评审员。调研主题：{topic}\n"
    "补充说明：{direction}\n"
    "请逐篇判断以下论文是否与主题相关，给出相关性分数（0~1）与子领域分类。\n\n"
    "论文列表：\n{papers}\n\n"
    "输出 JSON：{{\"items\": [{{\"index\": 0, \"relevant\": true, \"score\": 0.65, "
    "\"category\": \"receiver_testing\"}}]}}\n"
    "要求：score≥0.6 视为 relevant；category 从 [receiver_testing, high_precision, "
    "integrity, multipath, ionosphere, interference, timing, integrated_navigation, "
    "sbass, new_signals, simulation, other] 中选。"
)


class Reviewer(Role):
    name = "reviewer"
    label = "评审员"

    async def score(self, topic: str, direction: str, batch: list) -> list[dict]:
        """批量打分，返回 [{index, relevant, score, category}]；失败返回 []。"""
        lines = []
        for idx, p in enumerate(batch):
            abstract = (p.get("abstract") or "")[:400]
            lines.append(f"{idx}. 《{p['title']}》({p.get('year')}) "
                         f"{p.get('venue') or ''}。摘要：{abstract}")
        try:
            data = await self._json(
                [{"role": "user", "content": SCORE_PROMPT.format(
                    topic=topic, direction=direction or "（无）",
                    papers="\n".join(lines))}],
                max_tokens=2000)
        except LLMError:
            return []
        if not isinstance(data, dict):
            return []
        items = data.get("items")
        return items if isinstance(items, list) else []
