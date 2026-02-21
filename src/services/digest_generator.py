from typing import Any, Optional

import structlog

from .llm_client import llm_client, get_prompt

logger = structlog.get_logger(__name__)


def _format_papers_block(papers: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, paper in enumerate(papers):
        title = paper.get("title") or "Untitled"
        score = paper.get("score")
        citations = paper.get("citations")
        year = paper.get("year")
        reason = paper.get("reason") or ""
        meta = f"score={score}, citations={citations}, {year}"
        lines.append(f"Paper {i}: {title} ({meta})")
        if reason:
            lines.append(f"  Reason: {reason}")
    return "\n".join(lines)


def _build_user_message(
    topic_sentence: str,
    papers_block: str,
    prev_summary: Optional[str] = None,
) -> str:
    parts = [
        f"Topic: {topic_sentence}",
        "Papers:",
        papers_block,
    ]
    if prev_summary:
        parts.append(f"Previous summary:\n{prev_summary}")
    return "\n\n".join(parts)


async def generate_field_overview(topic_sentence: str, papers: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    try:
        papers_block = _format_papers_block(papers)
        user_message = _build_user_message(topic_sentence, papers_block)
        return await llm_client.chat_json(
            user_message=user_message,
            system_message=get_prompt("field_overview"),
            workflow="field_overview",
        )
    except Exception as e:
        logger.error("Field overview generation failed", error=str(e))
        return None


async def generate_weekly_digest(
    topic_sentence: str,
    papers: list[dict[str, Any]],
    prev_summary: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    try:
        papers_block = _format_papers_block(papers)
        user_message = _build_user_message(topic_sentence, papers_block, prev_summary=prev_summary)
        return await llm_client.chat_json(
            user_message=user_message,
            system_message=get_prompt("weekly_digest"),
            workflow="weekly_digest",
        )
    except Exception as e:
        logger.error("Weekly digest generation failed", error=str(e))
        return None


async def generate_monthly_report(
    topic_sentence: str,
    papers: list[dict[str, Any]],
    prev_summary: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    try:
        papers_block = _format_papers_block(papers)
        user_message = _build_user_message(topic_sentence, papers_block, prev_summary=prev_summary)
        return await llm_client.chat_json(
            user_message=user_message,
            system_message=get_prompt("monthly_report"),
            workflow="monthly_report",
        )
    except Exception as e:
        logger.error("Monthly report generation failed", error=str(e))
        return None
