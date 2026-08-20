"""文献源基类与统一归一化。"""
import abc
import re


class SourceError(Exception):
    """源级错误（含限流、网络、解析失败）。"""


class SourceRateLimited(SourceError):
    pass


def strip_html(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"<[^>]+>", " ", s)


def clean_text(s) -> str:
    if not s:
        return ""
    return " ".join(str(s).split())


def reconstruct_abstract(inverted_index) -> str:
    """OpenAlex 的 abstract_inverted_index 还原为正文。"""
    if not inverted_index:
        return ""
    pos = {}
    for word, positions in inverted_index.items():
        for p in positions:
            pos[p] = word
    if not pos:
        return ""
    return " ".join(pos[i] for i in sorted(pos))


class Source(abc.ABC):
    name: str = "base"
    label: str = "Base"
    requires_key: bool = False
    hint: str = ""

    def __init__(self, mailto: str = ""):
        self.mailto = (mailto or "").strip()

    @abc.abstractmethod
    async def search(self, query: str, year_from: int | None,
                     year_to: int | None, limit: int = 50) -> list[dict]:
        """检索并返回统一 Paper 字典列表。"""
