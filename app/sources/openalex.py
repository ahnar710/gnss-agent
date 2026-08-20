"""OpenAlex 源（主源）：全球开放文献图谱，免费、覆盖广、支持引用网络挖掘。"""
import httpx

from .base import Source, SourceError, clean_text, reconstruct_abstract

API = "https://api.openalex.org"


class OpenAlexSource(Source):
    name = "openalex"
    label = "OpenAlex"

    async def _get(self, client: httpx.AsyncClient, url: str, params: dict) -> dict:
        resp = await client.get(url, params=params)
        if resp.status_code == 429:
            raise SourceError("OpenAlex 限流(429)")
        resp.raise_for_status()
        return resp.json()

    async def search(self, query: str, year_from: int | None,
                     year_to: int | None, limit: int = 50) -> list[dict]:
        params = {
            "search": query,
            "per-page": min(max(limit, 1), 200),
            "sort": "relevance_score:desc",
        }
        if self.mailto:
            params["mailto"] = self.mailto
        filters = []
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                data = await self._get(client, f"{API}/works", params)
        except httpx.HTTPError as e:
            raise SourceError(f"OpenAlex 网络错误: {e}") from e
        return [self._normalize(w, query) for w in data.get("results", [])]

    def _normalize(self, w: dict, query: str) -> dict:
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        oa = w.get("open_access") or {}
        url = loc.get("landing_page_url") or oa.get("oa_url") or w.get("doi")
        authors = [a.get("author", {}).get("display_name")
                   for a in (w.get("authorships") or [])]
        return {
            "source": self.name,
            "doi": doi,
            "title": clean_text(w.get("title")),
            "authors": [a for a in authors if a],
            "year": w.get("publication_year"),
            "venue": clean_text(src.get("display_name")),
            "abstract": clean_text(reconstruct_abstract(w.get("abstract_inverted_index"))),
            "url": url,
            "cited_by": w.get("cited_by_count") or 0,
            "query_used": query,
            "_openalex_id": w.get("id"),
            "_referenced": w.get("referenced_works") or [],
        }

    async def referenced_works(self, openalex_id: str) -> list[str]:
        """获取某篇论文的参考文献（OpenAlex work id 列表），用于引用网络挖掘。"""
        wid = (openalex_id or "").rsplit("/", 1)[-1]
        if not wid:
            return []
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                data = await self._get(client, f"{API}/works/{wid}",
                                       {"select": "referenced_works"})
            return data.get("referenced_works") or []
        except (httpx.HTTPError, SourceError):
            return []

    async def fetch_works_by_ids(self, ids: list[str], limit: int = 100) -> list[dict]:
        """按 OpenAlex work id 批量取论文（用于引用网络挖掘）。"""
        wids = [i.rsplit("/", 1)[-1] for i in ids if i]
        out: list[dict] = []
        for i in range(0, len(wids), 50):
            chunk = wids[i:i + 50]
            params = {
                "filter": "ids.openalex:" + "|".join(chunk),
                "per-page": min(len(chunk), 200),
            }
            if self.mailto:
                params["mailto"] = self.mailto
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    data = await self._get(client, f"{API}/works", params)
            except httpx.HTTPError as e:
                raise SourceError(f"OpenAlex 批量获取失败: {e}") from e
            for w in data.get("results", []):
                out.append(self._normalize(w, "citation"))
            if len(out) >= limit:
                break
        return out[:limit]
