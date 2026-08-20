"""多 Agent 角色集（RoleSet）：一次构建五个专职 Agent，供协调器路由。

协作模式：角色间不对话，通过 SQLite 黑板（论文/日志/成本）协作；
每个角色可配置独立模型（成本分层），共享同一 base_url/api_key。
"""
from .analyst import Analyst
from .base import Role
from .editor import Editor
from .reader import Reader
from .reviewer import Reviewer
from .strategist import Strategist

# 角色 → 设置项中的模型覆盖键（空 = 用全局模型）
ROLE_MODEL_KEYS = {
    "strategist": "model_strategist",
    "reviewer": "model_reviewer",
    "reader": "model_reader",
    "analyst": "model_analyst",
    "editor": "model_editor",
}

ROLE_INFO = [
    {"name": "strategist", "label": "策略官", "desc": "主题解析与检索策略"},
    {"name": "reviewer", "label": "评审员", "desc": "相关性打分与子领域分类"},
    {"name": "reader", "label": "深读员", "desc": "逐篇中文结构化深读"},
    {"name": "analyst", "label": "分析师", "desc": "研究趋势与空白分析"},
    {"name": "editor", "label": "主编(质控)", "desc": "深读摘要忠实性核验"},
]


class RoleSet:
    """按设置构建五角色；record_usage: async (llm, usage) -> None。"""

    def __init__(self, settings: dict, llm_factory, record_usage):
        def role_llm(model_override: str | None):
            return llm_factory(settings, model_override)

        async def usage(llm, usage):
            if record_usage:
                await record_usage(llm, usage)

        self.strategist = Strategist(role_llm, settings.get(ROLE_MODEL_KEYS["strategist"], ""), usage)
        self.reviewer = Reviewer(role_llm, settings.get(ROLE_MODEL_KEYS["reviewer"], ""), usage)
        self.reader = Reader(role_llm, settings.get(ROLE_MODEL_KEYS["reader"], ""), usage)
        self.analyst = Analyst(role_llm, settings.get(ROLE_MODEL_KEYS["analyst"], ""), usage)
        self.editor = Editor(role_llm, settings.get(ROLE_MODEL_KEYS["editor"], ""), usage)

    def all_roles(self) -> list[Role]:
        return [self.strategist, self.reviewer, self.reader,
                self.analyst, self.editor]


__all__ = ["Role", "RoleSet", "ROLE_MODEL_KEYS", "ROLE_INFO",
           "Strategist", "Reviewer", "Reader", "Analyst", "Editor"]
