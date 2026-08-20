"""Semantic Scholar API 源：语义相关性检索 + 引用量 + 开放 PDF。
注意：未认证限流约 100 次/5 分钟，需在进程内做间隔控制与 429 退避。"""
import asyncio
import time

import httpx

from .base import Source, SourceError, SourceRateLimited, clean_text

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,authors,year,venue,externalIds,citationCount,url,openAccessPdf"
MIN_INTERVAL = 3.2  # 秒；~100 req/5min 的安全间隔


class SemanticScholarSource(Source):
    name = "semanticscholar"
    label = "Semantic Scholar"
    _lock = asyncio.Lock()
    _last_call = 0.0

    async def search(self, query: str, year_from: int | None,
                     year_to: int | None, limit: int = 100) -> list[dict]:
        async with SemanticScholarSource._lock:
            wait = MIN_INTERVAL - (time.monotonic() - SemanticScholarSource._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            params = {
                "query": query,
                "fields": FIELDS,
                "limit": min(max(limit, 1), 100),
            }
            if year_from and year_to:
                params["year"] = f"{year_from}-{year_to}"
            elif year_from:
                params["year"] = f"{year_from}-"
            elif year_to:
                params["year"] = f"-{year_to}"
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.get(API, params=params)
            except httpx.HTTPError as e:
                raise SourceError(f"Semantic Scholar 网络错误: {e}") from e
            finally:
                SemanticScholarSource._last_call = time.monotonic()

        if resp.status_code == 429:
            raise SourceRateLimited("Semantic Scholar 限流(429)，稍后重试")
        if resp.status_code != 200:
            raise SourceError(f"Semantic Scholar 返回 {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        results = []
        for p in data.get("data") or []:
            paper = self._normalize(p, query)
            if paper["title"]:
                results.append(paper)
        return results

    def _normalize(self, p: dict, query: str) -> dict:
        ext = p.get("externalIds") or {}
        oa = p.get("openAccessPdf") or {}
        return {
            "source": self.name,
            "doi": (ext.get("DOI") or "").strip() or None,
            "title": clean_text(p.get("title")),
            "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
            "year": year,
            "venue": clean_text(p.get("venue")),
            "abstract": clean_text(p.get("abstract")),
            "url": oa.get("url") or p.get("url"),
            "cited_by": p.get("citationCount") or 0,
            "query_used": query,
        }
