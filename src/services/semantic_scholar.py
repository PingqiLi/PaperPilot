"""
Semantic Scholar API v1.0.0 - search and citation data
"""
import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"

_S2_MIN_INTERVAL = 1.1
_s2_last_request: float = 0.0


async def _s2_rate_limit():
    global _s2_last_request
    now = time.monotonic()
    wait = _S2_MIN_INTERVAL - (now - _s2_last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _s2_last_request = time.monotonic()


class SemanticScholarService:

    def __init__(self):
        self.headers = {"User-Agent": "PaperAgent/1.0"}
        api_key = settings.s2_api_key
        if api_key:
            self.headers["x-api-key"] = api_key

    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_start: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if fields is None:
            fields = (
                "paperId,externalIds,title,abstract,authors,year,"
                "citationCount,venue,publicationDate"
            )

        url = f"{S2_API_BASE}/paper/search"
        params: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),
            "fields": fields,
        }
        if year_start:
            params["year"] = f"{year_start}-"

        all_papers: List[Dict[str, Any]] = []
        offset = 0
        retry_count = 0
        max_retries = 3

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while len(all_papers) < limit:
                    params["offset"] = offset
                    await _s2_rate_limit()
                    response = await client.get(url, params=params, headers=self.headers)

                    if response.status_code == 429:
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.warning("S2 rate limit exceeded max retries")
                            break
                        wait_time = 5 * retry_count
                        logger.warning("S2 rate limit, backing off", wait=wait_time)
                        await asyncio.sleep(wait_time)
                        continue

                    retry_count = 0
                    response.raise_for_status()
                    data = response.json()

                    papers = data.get("data", [])
                    if not papers:
                        break

                    all_papers.extend(papers)
                    offset += len(papers)

                    if offset >= data.get("total", 0):
                        break

            logger.info("S2 search completed", query=query[:50], found=len(all_papers))
            return all_papers[:limit]

        except Exception as e:
            logger.error("S2 search error", query=query, error=str(e))
            return []


    async def get_recommendations(
        self,
        paper_ids: List[str],
        negative_paper_ids: Optional[List[str]] = None,
        limit: int = 50,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not paper_ids:
            return []
        if fields is None:
            fields = (
                "paperId,externalIds,title,abstract,authors,year,"
                "citationCount,venue,publicationDate"
            )

        url = "https://api.semanticscholar.org/recommendations/v1/papers"
        payload = {
            "positivePaperIds": paper_ids[:5],
            "negativePaperIds": (negative_paper_ids or [])[:5],
        }
        params = {"fields": fields, "limit": min(limit, 100)}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await _s2_rate_limit()
                response = await client.post(
                    url, json=payload, params=params, headers=self.headers,
                )
                if response.status_code == 429:
                    logger.warning("S2 recommendations rate limited")
                    return []
                response.raise_for_status()
                papers = response.json().get("recommendedPapers", [])
                logger.info("S2 recommendations fetched", input=len(paper_ids), results=len(papers))
                return papers
        except Exception as e:
            logger.error("S2 recommendations error", error=str(e))
            return []


    async def get_citations(
        self,
        paper_id: str,
        limit: int = 1000,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if fields is None:
            fields = (
                "paperId,externalIds,title,abstract,authors,year,"
                "citationCount,influentialCitationCount,venue,"
                "publicationVenue,publicationTypes,publicationDate"
            )

        url = f"{S2_API_BASE}/paper/{paper_id}/citations"
        all_citations: List[Dict[str, Any]] = []
        offset = 0
        page_size = 500

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while len(all_citations) < limit:
                    await _s2_rate_limit()
                    response = await client.get(url, params={
                        "fields": f"citingPaper.{fields}",
                        "limit": page_size,
                        "offset": offset,
                    }, headers=self.headers)

                    if response.status_code == 429:
                        logger.warning("S2 citations rate limited", paper_id=paper_id)
                        break
                    response.raise_for_status()
                    data = response.json().get("data", [])
                    if not data:
                        break

                    for entry in data:
                        citing = entry.get("citingPaper")
                        if citing and citing.get("paperId"):
                            all_citations.append(citing)

                    offset += len(data)
                    if offset >= response.json().get("total", 0):
                        break

            logger.info("S2 citations fetched", paper_id=paper_id[:12], count=len(all_citations))
            return all_citations[:limit]
        except Exception as e:
            logger.error("S2 citations error", paper_id=paper_id, error=str(e))
            return []


semantic_scholar = SemanticScholarService()
