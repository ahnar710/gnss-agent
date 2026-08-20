"""文献源注册表：MVP 四源（全部免费开放 API）。"""
from .arxiv import ArxivSource
from .base import Source, SourceError, SourceRateLimited
from .crossref import CrossrefSource
from .openalex import OpenAlexSource
from .semanticscholar import SemanticScholarSource

ALL_SOURCES: list[type[Source]] = [
    OpenAlexSource,
    ArxivSource,
    SemanticScholarSource,
    CrossrefSource,
]


def build_sources(enabled_names: list[str], mailto: str = "") -> list[Source]:
    enabled = set(enabled_names or [])
    return [cls(mailto) for cls in ALL_SOURCES if cls.name in enabled]


def source_info() -> list[dict]:
    return [
        {
            "name": cls.name,
            "label": cls.label,
            "requires_key": cls.requires_key,
            "hint": cls.hint,
        }
        for cls in ALL_SOURCES
    ]


__all__ = [
    "Source", "SourceError", "SourceRateLimited",
    "ALL_SOURCES", "build_sources", "source_info",
]
