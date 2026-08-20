"""应用配置：路径、端口、默认设置。"""
import os
import sys
from pathlib import Path

APP_NAME = "GNSS 文献调研 Agent"
VERSION = "0.1.0"
DEFAULT_PORT = int(os.environ.get("GNSS_AGENT_PORT", "8765"))
HOST = "127.0.0.1"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def data_dir() -> Path:
    env = os.environ.get("GNSS_AGENT_DATA")
    if env:
        d = Path(env)
    elif is_frozen():
        # 打包后的应用把数据写到用户目录，避免写入失败
        d = Path.home() / ".gnss_agent"
    else:
        d = Path(__file__).resolve().parent.parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "tasks.db"


def reports_dir() -> Path:
    d = data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def uploads_dir() -> Path:
    """用户上传的 PDF 论文存放目录。"""
    d = data_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"

# 默认设置（用户可在 UI 中修改，持久化到 settings 表）
DEFAULT_SETTINGS = {
    "api_base": "https://api.deepseek.com/v1",
    "api_key": "",
    "model": "deepseek-chat",
    "target_count": "100",
    "time_limit_hours": "24",
    "year_back": "10",
    "relevance_threshold": "0.6",
    "max_concurrent_tasks": "3",
    "sources_enabled": '["openalex","arxiv","semanticscholar","crossref"]',
    # 成本估算与上限（USD）：单价按百万 token 计；上限 0=不限
    "price_in_per_m": "0.27",
    "price_out_per_m": "1.10",
    "max_task_cost_usd": "10",
    # 多 Agent 协作
    "reader_pool_size": "3",       # 深读员并行数（1~6）
    "qc_enabled": "1",             # 主编质控开关（1=开）
    "model_strategist": "",        # 各角色独立模型（留空 = 用全局模型）
    "model_reviewer": "",
    "model_reader": "",
    "model_analyst": "",
    "model_editor": "",
}

# 内置 GNSS 子领域（用于打分分类与查询扩展）
GNSS_SUBFIELDS = [
    "receiver_testing", "high_precision", "integrity", "multipath",
    "ionosphere", "interference", "timing", "integrated_navigation",
    "sbass", "new_signals", "simulation",
]
