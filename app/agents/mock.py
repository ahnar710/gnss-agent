"""演示/测试用假 LLM：不调用任何 API，返回确定性的结构化输出。

仅在设置环境变量 GNSS_AGENT_MOCK_LLM=1 时启用（README 有说明），
用于无 API Key 时体验界面或做自动化验证。生产使用必须配置真实 Key。
"""
import json
import re


class MockLLM:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = "mock",
                 price_in_per_m: float = 0.27, price_out_per_m: float = 1.10):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.price_in_per_m = price_in_per_m
        self.price_out_per_m = price_out_per_m

    @property
    def configured(self) -> bool:
        return True

    async def chat(self, messages: list, **kwargs) -> str:
        content = messages[-1]["content"]
        if "检索策略" in content:
            return json.dumps({
                "en_terms": ["GNSS multipath mitigation", "RTK urban canyon NLOS",
                             "GNSS receiver testing"],
                "zh_terms": ["多路径抑制", "城市峡谷定位"],
                "subfields": ["multipath", "receiver_testing"],
                "year_from": None,
            }, ensure_ascii=False)
        if "相关性评审员" in content:
            idxs = re.findall(r"^(\d+)\. 《", content, re.M)
            return json.dumps({
                "items": [{"index": int(i), "relevant": True, "score": 0.82,
                           "category": "multipath"} for i in idxs]
            }, ensure_ascii=False)
        if "质控员" in content:
            idxs = re.findall(r"^(\d+)\. 标题：", content, re.M)
            return json.dumps({
                "items": [{"index": int(i), "ok": True, "note": "通过"} for i in idxs]
            }, ensure_ascii=False)
        if "中文深读" in content:
            title = re.search(r"标题：(.+)", content)
            return json.dumps({
                "summary": f"该论文围绕 GNSS 多路径抑制开展研究，提出了改进算法并通过仿真与实测验证了定位精度提升，对接收机测试场景设计有参考价值。"
                           + (f"（标题：{title.group(1)[:40]}）" if title else ""),
                "methods": ["信号相关域分析", "实验验证"],
                "findings": ["多路径抑制显著提升定位精度", "算法复杂度可控"],
                "relevance": "可指导接收机多路径测试用例与场景设计",
                "category": "multipath",
            }, ensure_ascii=False)
        if "新的英文检索 query" in content:
            return json.dumps({
                "queries": ["3D mapping aided GNSS NLOS", "multipath mitigation machine learning",
                            "GNSS receiver multipath field test"]
            }, ensure_ascii=False)
        if "研究趋势与空白" in content:
            return ("## 研究趋势与热点\n"
                    "- 多路径抑制从信号处理向环境感知（3D 地图、视觉）融合演进\n"
                    "- 深度学习在 NLOS 识别中的应用快速增长\n\n"
                    "## 研究空白与机会\n"
                    "- 面向测试厂商的标准化多路径测试场景研究较少\n\n"
                    "## 对 GNSS 测试设备厂商的启示\n"
                    "- 模拟器产品应内置城市峡谷多路径场景库\n"
                    "- 关注 AI 辅助接收机测试的新兴需求")
        return "OK"

    async def chat_full(self, messages: list, **kwargs) -> tuple[str, dict]:
        """返回 (文本, usage)；usage 为空表示无 token 计量（演示模式）。"""
        return await self.chat(messages, **kwargs), {}

    async def chat_json_full(self, messages: list, **kwargs) -> tuple[dict, dict]:
        return json.loads(await self.chat(messages, **kwargs)), {}

    async def chat_json(self, messages: list, **kwargs):
        return json.loads(await self.chat(messages, **kwargs))

    def estimate_cost(self, usage: dict) -> float:
        return 0.0

    async def test(self) -> str:
        return "（演示模式，未连接真实模型）"
