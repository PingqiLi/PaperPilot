"""
ArXiv API client - 布尔搜索补充S2语义搜索覆盖不到的论文
"""
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
MAX_PER_REQUEST = 500
RATE_LIMIT_DELAY = 3.0


class ArxivService:

    def _build_category_clause(self, categories: List[str]) -> str:
        if not categories:
            return ""
        if len(categories) == 1:
            return f"cat:{categories[0]}"
        return "(" + " OR ".join(f"cat:{c}" for c in categories) + ")"

    def _keyword_to_abs_clauses(self, keyword: str) -> List[str]:
        keyword = keyword.strip()
        if not keyword:
            return []
        if " " in keyword:
            words = [w for w in keyword.split() if len(w) > 2]
            return [f"abs:{w}" for w in words]
        return [f"abs:{keyword}"]

    def _build_query(
        self,
        categories: List[str],
        keywords: List[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        parts = []

        cat_clause = self._build_category_clause(categories)
        if cat_clause:
            parts.append(cat_clause)

        for kw in keywords:
            parts.extend(self._keyword_to_abs_clauses(kw))

        query = " AND ".join(parts)

        if date_from or date_to:
            df = date_from or "190001010000"
            dt = date_to or "299912312359"
            query += f" AND submittedDate:[{df} TO {dt}]"

        return query

    def generate_keyword_combinations(
        self,
        keywords: List[str],
        max_combinations: int = 4,
    ) -> List[List[str]]:
        if not keywords:
            return []
        if len(keywords) <= 2:
            return [keywords]

        core = keywords[:min(len(keywords), 5)]
        combos: List[List[str]] = []
        for i in range(len(core)):
            for j in range(i + 1, len(core)):
                combos.append([core[i], core[j]])
                if len(combos) >= max_combinations:
                    return combos
        return combos

    def _parse_entry(self, entry: ET.Element) -> Optional[Dict[str, Any]]:
        id_url = entry.findtext("atom:id", default="", namespaces=ARXIV_NS)
        if "/abs/" not in id_url:
            return None

        arxiv_id = id_url.split("/abs/")[-1]
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.rsplit("v", 1)[0]

        title = entry.findtext("atom:title", default="", namespaces=ARXIV_NS)
        title = " ".join(title.split())

        abstract = entry.findtext("atom:summary", default="", namespaces=ARXIV_NS)
        abstract = " ".join(abstract.split())

        authors = []
        for author_el in entry.findall("atom:author", namespaces=ARXIV_NS):
            name = author_el.findtext("atom:name", default="", namespaces=ARXIV_NS)
            if name:
                authors.append({"name": name})

        published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
        pub_date = None
        year = None
        if published:
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                pub_date = dt.strftime("%Y-%m-%d")
                year = dt.year
            except ValueError:
                pass

        primary_cat = ""
        pcat_elem = entry.find("arxiv:primary_category", namespaces=ARXIV_NS)
        if pcat_elem is not None:
            primary_cat = pcat_elem.get("term", "")

        categories = []
        for cat_el in entry.findall("atom:category", namespaces=ARXIV_NS):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        return {
            "paperId": None,
            "externalIds": {"ArXiv": arxiv_id},
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "publicationDate": pub_date,
            "citationCount": 0,
            "influentialCitationCount": 0,
            "venue": "",
            "publicationVenue": None,
            "publicationTypes": None,
            "_arxiv_categories": categories,
            "_arxiv_primary_category": primary_cat,
            "_source": "arxiv",
        }

    async def search(
        self,
        categories: List[str],
        keywords: List[str],
        max_results: int = 300,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        combos = self.generate_keyword_combinations(keywords)
        if not combos:
            logger.warning("ArXiv search skipped: no keyword combinations")
            return []

        all_papers: Dict[str, Dict] = {}
        per_query_limit = min(100, max_results)

        for i, combo in enumerate(combos):
            query = self._build_query(categories, combo, date_from, date_to)
            papers = await self._fetch_query(query, max_results=per_query_limit)

            for p in papers:
                aid = (p.get("externalIds") or {}).get("ArXiv", "")
                if aid and aid not in all_papers:
                    all_papers[aid] = p

            logger.info(
                "ArXiv query done",
                combo=combo,
                found=len(papers),
                unique_total=len(all_papers),
            )

            if i < len(combos) - 1:
                await asyncio.sleep(RATE_LIMIT_DELAY)

        results = sorted(
            all_papers.values(),
            key=lambda p: p.get("publicationDate") or "0000-00-00",
            reverse=True,
        )
        return results[:max_results]

    async def _fetch_query(
        self,
        query: str,
        max_results: int = 300,
    ) -> List[Dict[str, Any]]:
        papers: List[Dict[str, Any]] = []
        start = 0
        per_page = min(max_results, MAX_PER_REQUEST)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while start < max_results:
                    params = {
                        "search_query": query,
                        "start": start,
                        "max_results": min(per_page, max_results - start),
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                    }

                    response = await client.get(ARXIV_API_BASE, params=params)
                    response.raise_for_status()

                    root = ET.fromstring(response.text)
                    entries = root.findall("atom:entry", namespaces=ARXIV_NS)

                    if not entries:
                        break

                    parsed_count = 0
                    for entry in entries:
                        paper = self._parse_entry(entry)
                        if paper:
                            papers.append(paper)
                            parsed_count += 1

                    total_str = root.findtext(
                        "opensearch:totalResults",
                        default="0",
                        namespaces=ARXIV_NS,
                    )
                    total = int(total_str)

                    start += len(entries)
                    if start >= total or parsed_count == 0:
                        break

                    await asyncio.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            logger.error("ArXiv fetch error", query=query[:80], error=str(e))

        return papers
