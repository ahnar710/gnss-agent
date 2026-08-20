"""OpenAI 兼容大模型客户端（DeepSeek / OpenAI / 通义 / Ollama 等）。

- 只调用用户自己配置的 base_url + api_key + model
- 指数退避重试（429/5xx/网络错误），400 不重试
- 提供健壮的 JSON 提取（兼容输出被 Markdown 代码块包裹等）
- 返回 usage（token 数），支持按可配置单价估算费用（成本面板用）
"""
import asyncio
import json
import logging
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger("llm")

DEFAULT_TIMEOUT = 90.0
MAX_RETRIES = 3
RETRY_BASE_SEC = 2.0

# 默认单价（USD / 百万 token），可在设置页修改
DEFAULT_PRICE_IN_PER_M = 0.27
DEFAULT_PRICE_OUT_PER_M = 1.10


class LLMError(Exception):
    pass


def extract_json(text: str) -> Optional[Any]:
    """从模型输出中稳健提取 JSON。"""
    if not text:
        return None
    text = text.strip()
    # 去掉可能的 ```json ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 找第一个 { 到最后一个 } 或第一个 [ 到最后一个 ]
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        s = text.find(open_ch)
        e = text.rfind(close_ch)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                continue
    return None


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: float = DEFAULT_TIMEOUT,
                 price_in_per_m: float = DEFAULT_PRICE_IN_PER_M,
                 price_out_per_m: float = DEFAULT_PRICE_OUT_PER_M):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model or "deepseek-chat"
        self.timeout = timeout
        self.price_in_per_m = float(price_in_per_m or 0)
        self.price_out_per_m = float(price_out_per_m or 0)

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def estimate_cost(self, usage: dict) -> float:
        """按当前单价估算本次调用费用（USD）。"""
        if not usage:
            return 0.0
        return (usage.get("prompt_tokens", 0) / 1e6 * self.price_in_per_m
                + usage.get("completion_tokens", 0) / 1e6 * self.price_out_per_m)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def chat_full(self, messages: list, max_tokens: int = 2000,
                        temperature: float = 0.2,
                        json_mode: bool = False) -> tuple[str, dict]:
        """调用 chat completions，返回 (文本, usage)。重试 3 次后抛 LLMError。"""
        if not self.configured:
            raise LLMError("未配置模型（base_url/model），请在设置页完成配置")
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        content = data["choices"][0]["message"]["content"] or ""
                    except (KeyError, IndexError, TypeError) as e:
                        raise LLMError(f"响应格式异常: {e} | {str(data)[:200]}")
                    usage = data.get("usage") or {}
                    return content, {
                        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                        "completion_tokens": int(usage.get("completion_tokens") or 0),
                    }
                if resp.status_code in (400, 401, 403, 404, 422):
                    raise LLMError(
                        f"模型接口返回 {resp.status_code}: {resp.text[:300]}")
                last_err = LLMError(f"模型接口返回 {resp.status_code}: {resp.text[:200]}")
            except httpx.HTTPError as e:
                last_err = LLMError(f"网络错误: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BASE_SEC * (2 ** attempt))
        raise LLMError(f"重试 {MAX_RETRIES} 次仍失败: {last_err}")

    async def chat(self, messages: list, max_tokens: int = 2000,
                   temperature: float = 0.2, json_mode: bool = False) -> str:
        text, _ = await self.chat_full(messages, max_tokens=max_tokens,
                                       temperature=temperature, json_mode=json_mode)
        return text

    async def chat_json_full(self, messages: list, max_tokens: int = 2000,
                             temperature: float = 0.2) -> tuple[Any, dict]:
        """调用并要求 JSON，返回 (解析结果, usage)；解析失败返回 (None, usage)。"""
        text, usage = await self.chat_full(messages, max_tokens=max_tokens,
                                           temperature=temperature, json_mode=True)
        return extract_json(text), usage

    async def chat_json(self, messages: list, max_tokens: int = 2000,
                        temperature: float = 0.2) -> Optional[Any]:
        data, _ = await self.chat_json_full(messages, max_tokens=max_tokens,
                                            temperature=temperature)
        return data

    async def test(self) -> str:
        """连通性测试：返回模型的一句话回复。"""
        text = await self.chat(
            [{"role": "user", "content": "请回复：连接成功"}],
            max_tokens=20, temperature=0.0)
        return (text or "").strip()[:100]
