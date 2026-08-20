"""Crossref API 源：DOI 权威解析、期刊名补全、引用量交叉校验。"""
import httpx

from .base import Source, SourceError, clean_text, strip_html

API = "https://api.crossref.org/works"
SELECT = "DOI,title,author,issued,abstract,container-title,URL,is-referenced-by-count"


class CrossrefSource(Source):
    name = "crossref"
    label = "Crossref"

    async def search(self, query: str, year_from: int | None,
                     year_to: int | None, limit: int = 50) -> list[dict]:
        params = {
            "query.bibliographic": query,
            "rows": min(max(limit, 1), 30),
            "select": SELECT,
            "sort": "relevance",
        }
        filters = []
        if year_from:
            filters.append(f"from-pub-date:{year_from}-01-01")
        if year_to:
            filters.append(f"until-pub-date:{year_to}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        if self.mailto:
            params["mailto"] = self.mailto
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.get(API, params=params)
        except httpx.HTTPError as e:
            raise SourceError(f"Crossref 网络错误: {e}") from e
        if resp.status_code == 429:
            raise SourceError("Crossref 限流(429)")
        if resp.status_code != 200:
            raise SourceError(f"Crossref 返回 {resp.status_code}: {resp.text[:200]}")
        items = (resp.json().get("message") or {}).get("items") or []
        return [self._normalize(it, query) for it in items]

    def _normalize(self, it: dict, query: str) -> dict:
        title = it.get("title") or [""]
        authors = []
        for a in it.get("author") or []:
            name = " ".join(x for x in [a.get("given"), a.get("family")] if x)
            if name:
                authors.append(name)
        year = None
        parts = (it.get("issued") or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                year = int(parts[0][0])
            except (TypeError, ValueError, IndexError):
                year = None
        return {
            "source": self.name,
            "doi": (it.get("DOI") or "").strip() or None,
            "title": clean_text(title[0]),
            "authors": authors,
            "year": year,
            "venue": clean_text((it.get("container-title") or [""])[0]),
            "abstract": clean_text(strip_html(it.get("abstract") or "")),
            "url": it.get("URL"),
            "cited_by": it.get("is-referenced-by-count") or 0,
            "query_used": query,
        }
