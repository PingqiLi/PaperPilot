import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
import structlog

from ..database import get_db
from ..models import Digest, Paper, PaperRuleSet, RuleSet
from ..services import app_settings
from ..services.digest_generator import (
    generate_field_overview,
    generate_monthly_report,
    generate_weekly_digest,
)
from ..services.email_service import send_digest, format_digest_html
from ..services.markdown_formatter import format_digest_markdown

logger = structlog.get_logger(__name__)

router = APIRouter()


class DigestCreate(BaseModel):
    digest_type: str = Field(..., pattern="^(field_overview|weekly|monthly)$")


class DigestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ruleset_id: int
    digest_type: str
    content: dict[str, Any]
    paper_count: int
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime


class DigestListResponse(BaseModel):
    total: int
    items: list[DigestResponse]


_FIELD_OVERVIEW_MAX_PAPERS = 80


def _fetch_digest_papers(db: Session, ruleset_id: int, digest_type: str) -> tuple[list[Any], datetime | None, datetime | None]:
    now = datetime.utcnow()
    period_start: datetime | None = None
    period_end: datetime | None = None

    query = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(PaperRuleSet.ruleset_id == ruleset_id)

    if digest_type == "weekly":
        period_end = now
        period_start = now - timedelta(days=7)
        query = query.filter(Paper.published_date >= period_start)
    elif digest_type == "monthly":
        period_end = now
        period_start = now - timedelta(days=30)
        query = query.filter(Paper.published_date >= period_start)

    if digest_type == "field_overview":
        papers = query.order_by(
            PaperRuleSet.llm_score.desc().nullslast(),
            Paper.citation_count.desc().nullslast(),
        ).limit(_FIELD_OVERVIEW_MAX_PAPERS).all()
    else:
        papers = query.order_by(Paper.published_date.desc().nullslast()).all()
    return papers, period_start, period_end


def _to_generator_payload(rows: list[Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for paper, assoc in rows:
        payload.append(
            {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "score": assoc.llm_score,
                "citations": paper.citation_count,
                "year": paper.year,
                "reason": assoc.llm_reason,
            }
        )
    return payload


@router.get("/{ruleset_id}/digests", response_model=DigestListResponse)
def list_digests(
    ruleset_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    query = db.query(Digest).filter(Digest.ruleset_id == ruleset_id)
    total = query.count()
    rows = query.order_by(Digest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [DigestResponse.model_validate(item) for item in rows]
    return DigestListResponse(total=total, items=items)


@router.get("/{ruleset_id}/digests/{digest_id}", response_model=DigestResponse)
def get_digest(ruleset_id: int, digest_id: int, db: Session = Depends(get_db)):
    digest = db.query(Digest).filter(Digest.id == digest_id, Digest.ruleset_id == ruleset_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest不存在")
    return digest


@router.post("/{ruleset_id}/digests", response_model=DigestResponse)
async def create_digest(ruleset_id: int, data: DigestCreate, db: Session = Depends(get_db)):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    rows, period_start, period_end = _fetch_digest_papers(db, ruleset_id, data.digest_type)
    papers = _to_generator_payload(rows)

    prev_summary = None
    if data.digest_type in {"weekly", "monthly"}:
        prev_digest = db.query(Digest).filter(
            Digest.ruleset_id == ruleset_id,
            Digest.digest_type == data.digest_type,
        ).order_by(Digest.created_at.desc()).first()
        if prev_digest:
            prev_summary = json.dumps(prev_digest.content, ensure_ascii=False)

    topic_sentence = str(getattr(ruleset, "topic_sentence"))

    if data.digest_type == "field_overview":
        content = await generate_field_overview(topic_sentence, papers)
    elif data.digest_type == "weekly":
        content = await generate_weekly_digest(topic_sentence, papers, prev_summary=prev_summary)
    else:
        content = await generate_monthly_report(topic_sentence, papers, prev_summary=prev_summary)

    if content is None:
        logger.error("Digest generation failed", ruleset_id=ruleset_id, digest_type=data.digest_type)
        raise HTTPException(status_code=502, detail="Digest生成失败")

    content["paper_references"] = [
        {"index": i, "title": p.get("title", ""), "arxiv_id": p.get("arxiv_id", "")}
        for i, p in enumerate(papers)
    ]

    digest = Digest(
        ruleset_id=ruleset_id,
        digest_type=data.digest_type,
        content=content,
        paper_count=len(papers),
        period_start=period_start,
        period_end=period_end,
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)

    recipient = app_settings.get("digest_email_to")
    if recipient:
        topic_name = str(getattr(ruleset, "name"))
        type_labels = {"field_overview": "领域概览", "weekly": "周报", "monthly": "月报"}
        subject = f"[Paper Agent] {topic_name} — {type_labels.get(data.digest_type, data.digest_type)}"
        html_body = format_digest_html(content, data.digest_type, topic_name)
        try:
            send_digest(recipient, subject, html_body,
                        digest_id=digest.id, ruleset_id=ruleset_id,
                        topic_name=topic_name, digest_type=data.digest_type)
        except Exception:
            pass

    return digest


@router.get("/{ruleset_id}/digests/{digest_id}/markdown")
def export_digest_markdown(ruleset_id: int, digest_id: int, db: Session = Depends(get_db)):
    digest = db.query(Digest).filter(Digest.id == digest_id, Digest.ruleset_id == ruleset_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest不存在")

    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    topic_name = str(getattr(ruleset, "name")) if ruleset else "Unknown"

    md = format_digest_markdown(str(digest.digest_type), digest.content, topic_name)

    type_labels = {"field_overview": "领域概览", "weekly": "周报", "monthly": "月报"}
    label = type_labels.get(str(digest.digest_type), str(digest.digest_type))
    filename = f"{topic_name}_{label}_{digest.created_at.strftime('%Y%m%d')}.md"

    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
