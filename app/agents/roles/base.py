"""Agent 角色基类。

每个角色 = 独立提示词 + 独立 LLM 实例（可配置独立模型实现成本分层）+ usage 成本追踪。
角色间通过 SQLite（黑板模式）协作，不直接对话。
"""
from abc import ABC


class Role(ABC):
    name: str = "role"
    label: str = "角色"

    def __init__(self, llm_factory, model_override: str = "", record_usage=None):
        """llm_factory(settings, model_override|None) -> LLM 实例；
        record_usage: async (llm, usage) -> None，用于成本追踪。"""
        self._llm = llm_factory(model_override or None)
        self._record_usage = record_usage

    @property
    def configured(self) -> bool:
        return self._llm.configured

    @property
    def model(self) -> str:
        return getattr(self._llm, "model", "?")

    async def _json(self, messages: list, **kw):
        data, usage = await self._llm.chat_json_full(messages, **kw)
        if self._record_usage:
            await self._record_usage(self._llm, usage)
        return data

    async def _text(self, messages: list, **kw):
        text, usage = await self._llm.chat_full(messages, **kw)
        if self._record_usage:
            await self._record_usage(self._llm, usage)
        return text
