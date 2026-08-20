"""arXiv API 源：GNSS/PNT 预印本（信号处理、组合导航、抗干扰等前沿）。"""
import asyncio
import xml.etree.ElementTree as ET

import httpx

from .base import Source, SourceError, clean_text

API = "https://export.arxiv.org/api/query"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "ar": "http://arxiv.org/schemas/atom",
}


class ArxivSource(Source):
    name = "arxiv"
    label = "arXiv"

    async def search(self, query: str, year_from: int | None,
                     year_to: int | None, limit: int = 50) -> list[dict]:
        # arXiv 全短语检索过严，改为关键词 AND 组合（最多 8 词）
        terms = [t for t in query.split() if any(c.isalpha() for c in t)][:8]
        if not terms:
            terms = [query]
        search_query = " AND ".join(f"all:{t}" for t in terms)
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(max(limit, 1), 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.get(API, params=params)
        except httpx.HTTPError as e:
            # arXiv 偶发瞬时网络错误，重试一次
            try:
                await asyncio.sleep(2)
                async with httpx.AsyncClient(timeout=45) as client:
                    resp = await client.get(API, params=params)
            except httpx.HTTPError as e2:
                raise SourceError(f"arXiv 网络错误: {e2}") from e2
        if resp.status_code != 200:
            raise SourceError(f"arXiv 返回 {resp.status_code}")
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            raise SourceError(f"arXiv XML 解析失败: {e}") from e

        results = []
        for entry in root.findall("a:entry", NS):
            year = self._year(entry.findtext("a:published", namespaces=NS))
            if year_from and year and year < year_from:
                continue
            if year_to and year and year > year_to:
                continue
            p = self._normalize(entry, query)
            if p["title"]:
                results.append(p)
        return results

    def _year(self, published: str) -> int | None:
        try:
            return int((published or "")[:4])
        except (TypeError, ValueError):
            return None

    def _normalize(self, entry, query: str) -> dict:
        title = clean_text(entry.findtext("a:title", namespaces=NS))
        summary = clean_text(entry.findtext("a:summary", namespaces=NS))
        authors = [a.findtext("a:name", namespaces=NS)
                   for a in entry.findall("a:author", NS)]
        authors = [a for a in authors if a]
        doi_el = entry.find("ar:doi", NS)
        doi = clean_text(doi_el.text) if doi_el is not None and doi_el.text else None
        jref_el = entry.find("ar:journal_ref", NS)
        venue = clean_text(jref_el.text) if jref_el is not None and jref_el.text else None
        cat_el = entry.find("ar:primary_category", NS)
        if cat_el is None:
            cats = entry.findall("ar:category", NS)
            cat_el = cats[0] if cats else None
        category = (cat_el.get("term") or "") if cat_el is not None else ""
        return {
            "source": self.name,
            "doi": doi,
            "title": title,
            "authors": authors,
            "year": self._year(entry.findtext("a:published", namespaces=NS)),
            "venue": (venue or f"arXiv:{category}") if (venue or category) else None,
            "abstract": summary,
            "url": clean_text(entry.findtext("a:id", namespaces=NS)),
            "cited_by": 0,
            "query_used": query,
        }
