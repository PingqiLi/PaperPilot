"""
论文API路由 - v1.0.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Paper, PaperRuleSet, RuleSet
from ..schemas.paper import PaperResponse, PaperListResponse, PaperWithScore
from ..services import app_settings

router = APIRouter()


@router.get("", response_model=PaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=None, ge=1, le=100),
    status: str = Query(default=None),
    topic_id: int = Query(default=None),
    sort_by: str = Query(default="llm_score"),
    sort_order: str = Query(default="desc"),
    min_score: float = Query(default=0),
    db: Session = Depends(get_db),
):
    if page_size is None:
        page_size = app_settings.get_int("display_top_n")

    query = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).join(
        RuleSet, PaperRuleSet.ruleset_id == RuleSet.id
    ).filter(RuleSet.is_active == True)

    if status == "highlighted":
        threshold = app_settings.get_int("highlight_threshold")
        query = query.filter(PaperRuleSet.llm_score >= threshold)
    elif status:
        query = query.filter(PaperRuleSet.status == status)
    if topic_id:
        query = query.filter(PaperRuleSet.ruleset_id == topic_id)
    if min_score > 0:
        query = query.filter(PaperRuleSet.llm_score >= min_score)

    if sort_by == "llm_score":
        order_col = PaperRuleSet.llm_score
    elif sort_by == "impact_score":
        order_col = Paper.impact_score
    elif sort_by == "citation_count":
        order_col = Paper.citation_count
    else:
        order_col = Paper.published_date

    if sort_order == "desc":
        query = query.order_by(order_col.desc().nullslast())
    else:
        query = query.order_by(order_col.asc().nullsfirst())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    papers = []
    for paper, assoc in items:
        papers.append(PaperWithScore(
            id=paper.id,
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors or [],
            abstract=paper.abstract,
            categories=paper.categories or [],
            published_date=paper.published_date,
            year=paper.year,
            venue=paper.venue,
            pdf_url=paper.pdf_url,
            citation_count=paper.citation_count or 0,
            impact_score=paper.impact_score or 0.0,
            is_survey=paper.is_survey or False,
            llm_score=assoc.llm_score,
            llm_reason=assoc.llm_reason,
            status=assoc.status or "inbox",
            source=assoc.source or "initialize",
            topic_id=assoc.ruleset_id,
        ))

    return PaperListResponse(total=total, page=page, page_size=page_size, items=papers)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return paper
