"""
论文深度分析服务 - 抓取论文内容并通过LLM生成结构化分析报告
"""
import re
from html.parser import HTMLParser
from typing import Optional

import httpx
import structlog

from .llm_client import llm_client, get_prompt

logger = structlog.get_logger(__name__)

MAX_CONTENT_CHARS = 12000


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_tags = {"script", "style", "nav", "header", "footer", "aside"}
        self._current_skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag):
        if tag in self._skip_tags and self._current_skip > 0:
            self._current_skip -= 1

    def handle_data(self, data):
        if self._current_skip == 0:
            text = data.strip()
            if text:
                self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


async def _fetch_ar5iv(arxiv_id: str) -> Optional[str]:
    url = f"https://ar5iv.org/html/{arxiv_id}"
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "PaperPilot/1.0"})
            if resp.status_code != 200:
                return None
            html = resp.text
            if "404" in html[:500] or len(html) < 2000:
                return None
            text = _html_to_text(html)
            return text[:MAX_CONTENT_CHARS] if text else None
    except Exception as e:
        logger.warning("ar5iv fetch failed", arxiv_id=arxiv_id, error=str(e))
        return None


def _build_paper_context(
    title: str,
    authors: list[str],
    abstract: Optional[str],
    year: Optional[int],
    venue: Optional[str],
    citation_count: int,
    full_text: Optional[str],
) -> str:
    lines = [
        f"Title: {title}",
        f"Authors: {', '.join(authors[:10])}",
        f"Year: {year or 'Unknown'}",
        f"Venue: {venue or 'Unknown'}",
        f"Citations: {citation_count}",
        "",
        "Abstract:",
        abstract or "(not available)",
    ]
    if full_text:
        lines += ["", "Full Paper Content (truncated):", full_text]
    return "\n".join(lines)


async def analyze_paper(
    arxiv_id: str,
    title: str,
    authors: list[str],
    abstract: Optional[str],
    year: Optional[int],
    venue: Optional[str],
    citation_count: int,
) -> dict:
    full_text = None
    if arxiv_id and not arxiv_id.startswith("s2:"):
        full_text = await _fetch_ar5iv(arxiv_id)
        if full_text:
            logger.info("ar5iv content fetched", arxiv_id=arxiv_id, chars=len(full_text))
        else:
            logger.info("ar5iv unavailable, using abstract only", arxiv_id=arxiv_id)

    context = _build_paper_context(
        title=title,
        authors=authors,
        abstract=abstract,
        year=year,
        venue=venue,
        citation_count=citation_count,
        full_text=full_text,
    )

    prompt = f"{get_prompt('paper_analysis')}\n\n{context}"

    result = await llm_client.chat_json(
        user_message=prompt,
        system_message="You are an expert academic paper analyst. Output strict JSON only.",
        workflow="paper_analysis",
    )

    result["_source"] = "full_text" if full_text else "abstract_only"
    return result
