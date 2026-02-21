"""
批量LLM评分 - 每次5篇论文一起评分，降低API调用次数
"""
from typing import Dict, List, Optional

import structlog

from . import app_settings
from .llm_client import llm_client, load_prompt

logger = structlog.get_logger(__name__)

_SCORING_HEADER = """\
You are an expert academic paper relevance scorer.

Given a research topic and a batch of papers (title + metadata + abstract), \
score each paper's relevance to the topic on a scale of 1-10:"""

DEFAULT_SCORING_RUBRIC = """\
- 1-3: Not relevant or tangentially related
- 4-5: Somewhat relevant but not core
- 6-7: Relevant, worth reading
- 8-9: Highly relevant, important paper
- 10: Must-read, directly addresses the topic

Metadata signals — use these to ADJUST your scoring:
- **Citations**: High citation count (>100) suggests established importance. \
Low citations on a recent paper is normal — do not penalize.
- **Venue**: Top venues (NeurIPS, ICML, ICLR, ACL, CVPR, Nature, Science, etc.) \
suggest higher quality. Use as a tiebreaker, not a primary signal.
- **Impact score**: Pre-computed composite score (0-1). Papers with impact > 0.5 \
deserve extra attention.
- **Year**: Recent papers (last 2 years) are more valuable for tracking trends. \
Older papers need higher citations to justify relevance.
- **Survey/Review**: Marked as "Type: Survey/Review" in metadata."""

_SCORING_FOOTER = """\
Survey/review control:
- If a paper is a survey, review, tutorial, or benchmark overview, cap its score \
at 7 UNLESS it is highly specific to the topic AND published within the last 2 years.
- Prefer original research over surveys — a focused empirical paper that advances \
the field is more valuable than a broad survey.
- Recency matters: a recent survey that synthesizes latest progress is more useful \
than an outdated one. Penalize surveys older than 3 years.

Output strict JSON: {"scores": [{"index": 0, "score": 7, "reason": "..."}, ...]}
Keep reasons concise (1 sentence). Score ALL papers in the batch."""


def _get_scoring_prompt() -> str:
    custom_rubric = app_settings.get("prompt_batch_scoring_rubric")
    if not custom_rubric:
        return load_prompt("batch_scoring.md")
    return f"{_SCORING_HEADER}\n{custom_rubric}\n\n{_SCORING_FOOTER}"


def _format_paper_block(i: int, p: Dict) -> str:
    title = p.get("title", "Unknown")
    abstract = (p.get("abstract") or "")[:500]

    meta_parts = []
    year = p.get("year")
    if year:
        meta_parts.append(f"Year: {year}")
    venue = p.get("venue")
    if venue:
        meta_parts.append(f"Venue: {venue}")
    citations = p.get("citation_count")
    if citations is not None:
        meta_parts.append(f"Citations: {citations}")
    impact = p.get("impact_score")
    if impact is not None:
        meta_parts.append(f"Impact: {impact:.2f}")
    if p.get("is_survey"):
        meta_parts.append("Type: Survey/Review")

    meta_line = " | ".join(meta_parts) if meta_parts else ""
    block = f"Paper {i}:\nTitle: {title}\n"
    if meta_line:
        block += f"    {meta_line}\n"
    block += f"{abstract}\n\n"
    return block


def _build_preference_context(
    favorited: Optional[List[Dict]] = None,
    archived: Optional[List[Dict]] = None,
) -> str:
    sections = []
    if favorited:
        lines = []
        for p in favorited[:5]:
            reason = p.get("reason", "")
            line = f"- \"{p.get('title', '')}\""
            if reason:
                line += f" — {reason}"
            lines.append(line)
        sections.append("User's highly-valued papers (positive examples):\n" + "\n".join(lines))
    if archived:
        lines = [f"- \"{p.get('title', '')}\"" for p in archived[:3]]
        sections.append("Papers the user marked as not relevant (negative examples):\n" + "\n".join(lines))
    if sections:
        return "\n\n".join(sections) + "\n\nUse these preferences to calibrate your scoring.\n\n"
    return ""


async def score_batch(
    topic_sentence: str,
    papers: List[Dict],
    favorited: Optional[List[Dict]] = None,
    archived: Optional[List[Dict]] = None,
) -> List[Dict]:
    if not papers:
        return []

    papers_text = ""
    for i, p in enumerate(papers):
        papers_text += _format_paper_block(i, p)

    pref_context = _build_preference_context(favorited, archived)
    prompt = f"Topic: {topic_sentence}\n\n{pref_context}Papers:\n{papers_text}"

    try:
        result = await llm_client.chat_json(
            user_message=prompt,
            system_message=_get_scoring_prompt(),
            workflow="batch_scoring",
        )
        scores = result.get("scores", [])

        validated = []
        for s in scores:
            validated.append({
                "index": s.get("index", 0),
                "score": max(1, min(10, s.get("score", 5))),
                "reason": s.get("reason", ""),
            })
        return validated

    except Exception as e:
        logger.error("Batch scoring failed", error=str(e))
        return [{"index": i, "score": 5, "reason": "评分失败"} for i in range(len(papers))]
