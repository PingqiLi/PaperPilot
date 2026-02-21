"""
规则集API路由 - v1.0.0
"""
import asyncio
import re
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.orm import Session
import structlog

from datetime import datetime

from ..database import get_db
from ..models import Paper, PaperRuleSet, RuleSet, Run
from ..schemas.paper import (
    PaperListResponse,
    PaperPreview,
    PaperStatusUpdate,
    PaperWithScore,
    RuleSetCreate,
    RuleSetDraftRequest,
    RuleSetDraftResponse,
    RuleSetResponse,
    RuleSetUpdate,
    RunCreate,
    RunResponse,
    TopicOverview,
    TopicPaperCounts,
)
from ..services import app_settings
from ..services.draft_generator import generate_draft
from ..services.impact_scoring import compute_impact_score, is_survey_paper
from ..services.pipeline import run_initialize, run_track
from ..services.semantic_scholar import SemanticScholarService
from ..services.task_manager import create_task, complete_task, fail_task, update_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/rulesets", tags=["rulesets"])


@router.post("/draft", response_model=RuleSetDraftResponse)
async def create_draft(req: RuleSetDraftRequest):
    preview = req.topic_sentence[:60] + ("..." if len(req.topic_sentence) > 60 else "")
    task = create_task("topic_init", f"New Topic: {preview}", status="running")
    try:
        draft = await generate_draft(req.topic_sentence)
        update_task(task.id, status="awaiting_approval")
        draft.task_id = task.id
        return draft
    except ValueError as e:
        fail_task(task.id, str(e))
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        fail_task(task.id, str(e))
        logger.error("Draft generation endpoint failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"LLM服务异常: {str(e)}")


@router.get("", response_model=List[RuleSetResponse])
def list_rulesets(db: Session = Depends(get_db)):
    return db.query(RuleSet).filter(RuleSet.is_active == True).all()


@router.get("/overview", response_model=List[TopicOverview])
def get_overview(db: Session = Depends(get_db)):
    from sqlalchemy import case, func

    rulesets = db.query(RuleSet).filter(
        RuleSet.is_active == True,
    ).order_by(RuleSet.display_order.asc(), RuleSet.id.asc()).all()
    result = []

    for rs in rulesets:
        counts_q = db.query(
            func.count(PaperRuleSet.id).label("total"),
            func.sum(case((PaperRuleSet.source == "initialize", 1), else_=0)).label("init_count"),
            func.sum(case((PaperRuleSet.source == "track", 1), else_=0)).label("track_count"),
            func.sum(case((PaperRuleSet.status == "favorited", 1), else_=0)).label("fav_count"),
        ).filter(PaperRuleSet.ruleset_id == rs.id).first()

        paper_counts = TopicPaperCounts(
            total=counts_q.total or 0,
            initialize=counts_q.init_count or 0,
            track=counts_q.track_count or 0,
            favorited=counts_q.fav_count or 0,
        )

        track_latest_count = 0
        latest_track_run = db.query(Run).filter(
            Run.ruleset_id == rs.id,
            Run.run_type == "track",
            Run.status == "completed",
        ).order_by(Run.completed_at.desc()).first()

        if latest_track_run and latest_track_run.started_at:
            track_latest_count = db.query(func.count(PaperRuleSet.id)).filter(
                PaperRuleSet.ruleset_id == rs.id,
                PaperRuleSet.source == "track",
                PaperRuleSet.created_at >= latest_track_run.started_at,
            ).scalar() or 0

        top_rows = db.query(Paper, PaperRuleSet).join(
            PaperRuleSet, Paper.id == PaperRuleSet.paper_id
        ).filter(
            PaperRuleSet.ruleset_id == rs.id,
        ).order_by(
            PaperRuleSet.llm_score.desc().nullslast()
        ).limit(5).all()

        top_papers = [
            PaperPreview(
                id=p.id,
                arxiv_id=p.arxiv_id,
                title=p.title,
                llm_score=a.llm_score,
                llm_reason=a.llm_reason,
                is_survey=p.is_survey or False,
                year=p.year,
                venue=p.venue,
            )
            for p, a in top_rows
        ]

        result.append(TopicOverview(
            id=rs.id,
            name=rs.name,
            topic_sentence=rs.topic_sentence,
            is_initialized=rs.is_initialized,
            created_at=rs.created_at,
            last_track_at=rs.last_track_at,
            track_latest_count=track_latest_count,
            paper_counts=paper_counts,
            top_papers=top_papers,
        ))

    return result


@router.post("", response_model=RuleSetResponse)
def create_ruleset(data: RuleSetCreate, db: Session = Depends(get_db)):
    existing = db.query(RuleSet).filter(RuleSet.name == data.name, RuleSet.is_active == True).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则集名称已存在")
    ruleset = RuleSet(**data.model_dump())
    db.add(ruleset)
    db.commit()
    db.refresh(ruleset)
    return ruleset


class ReorderRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1)


@router.put("/reorder")
def reorder_topics(data: ReorderRequest, db: Session = Depends(get_db)):
    for i, rs_id in enumerate(data.ids):
        db.query(RuleSet).filter(RuleSet.id == rs_id).update({"display_order": i})
    db.commit()
    return {"message": "排序已更新"}


@router.get("/{ruleset_id}", response_model=RuleSetResponse)
def get_ruleset(ruleset_id: int, db: Session = Depends(get_db)):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    return ruleset


@router.put("/{ruleset_id}", response_model=RuleSetResponse)
def update_ruleset(ruleset_id: int, data: RuleSetUpdate, db: Session = Depends(get_db)):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(ruleset, key, value)
    db.commit()
    db.refresh(ruleset)
    return ruleset


@router.delete("/{ruleset_id}")
def delete_ruleset(ruleset_id: int, db: Session = Depends(get_db)):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    ruleset.is_active = False
    db.commit()
    return {"message": "规则集已删除"}


@router.get("/{ruleset_id}/reinit-preview")
def reinit_preview(ruleset_id: int, db: Session = Depends(get_db)):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    total = db.query(func.count(PaperRuleSet.id)).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
    ).scalar() or 0

    favorited = db.query(func.count(PaperRuleSet.id)).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.status == "favorited",
    ).scalar() or 0

    will_remove = total - favorited

    return {
        "total": total,
        "favorited": favorited,
        "will_remove": will_remove,
    }


@router.post("/{ruleset_id}/runs", response_model=RunResponse)
async def create_run(
    ruleset_id: int,
    data: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    active_run = db.query(Run).filter(
        Run.ruleset_id == ruleset_id,
        Run.status.in_(["pending", "running"]),
    ).first()
    if active_run:
        raise HTTPException(status_code=409, detail="该规则集已有运行中的任务")

    if data.reinit and data.run_type == "initialize":
        deleted = db.query(PaperRuleSet).filter(
            PaperRuleSet.ruleset_id == ruleset_id,
            PaperRuleSet.status != "favorited",
        ).delete(synchronize_session="fetch")
        ruleset.is_initialized = False
        db.commit()
        logger.info("Re-init cleanup", ruleset_id=ruleset_id, papers_removed=deleted)

    run = Run(ruleset_id=ruleset_id, run_type=data.run_type)
    db.add(run)
    db.commit()
    db.refresh(run)

    topic_name = str(getattr(ruleset, "name", ""))
    type_label = "Initialize" if data.run_type == "initialize" else "Track"
    task_id = data.task_id

    if task_id:
        update_task(task_id, status="running", run_id=run.id, ruleset_id=ruleset_id)
    else:
        task = create_task(
            data.run_type, f"{type_label}: {topic_name}",
            ruleset_id=ruleset_id, run_id=run.id,
        )
        task_id = task.id

    if data.run_type == "initialize":
        background_tasks.add_task(run_initialize, run.id, ruleset_id, task_id)
    else:
        background_tasks.add_task(run_track, run.id, ruleset_id, task_id)

    return run


@router.get("/{ruleset_id}/runs", response_model=List[RunResponse])
def list_runs(ruleset_id: int, db: Session = Depends(get_db)):
    return db.query(Run).filter(Run.ruleset_id == ruleset_id).order_by(Run.created_at.desc()).all()


@router.get("/{ruleset_id}/runs/{run_id}", response_model=RunResponse)
def get_run(ruleset_id: int, run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id, Run.ruleset_id == ruleset_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return run


@router.get("/{ruleset_id}/papers", response_model=PaperListResponse)
def get_ruleset_papers(
    ruleset_id: int,
    page: int = 1,
    page_size: int = None,
    status: str = None,
    source: str = None,
    search: str = None,
    sort_by: str = "llm_score",
    sort_order: str = "desc",
    min_score: float = 0,
    db: Session = Depends(get_db),
):
    if page_size is None:
        page_size = app_settings.get_int("display_top_n")
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    query = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(PaperRuleSet.ruleset_id == ruleset_id)

    if status:
        query = query.filter(PaperRuleSet.status == status)
    if source:
        query = query.filter(PaperRuleSet.source == source)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            (Paper.title.ilike(like_term)) | (Paper.abstract.ilike(like_term))
        )
    if min_score > 0:
        query = query.filter(PaperRuleSet.llm_score >= min_score)

    latest_track_run = db.query(Run).filter(
        Run.ruleset_id == ruleset_id,
        Run.run_type == "track",
        Run.status == "completed",
    ).order_by(Run.completed_at.desc()).first()
    latest_track_start = latest_track_run.started_at if latest_track_run else None

    if sort_by == "llm_score":
        order_col = PaperRuleSet.llm_score
    elif sort_by == "impact_score":
        order_col = Paper.impact_score
    elif sort_by == "citation_count":
        order_col = Paper.citation_count
    else:
        order_col = Paper.published_date

    is_new_expr = case(
        (
            (PaperRuleSet.source == "track")
            & (latest_track_start is not None)
            & (PaperRuleSet.created_at >= latest_track_start),
            1,
        ),
        else_=0,
    ) if latest_track_start else None

    if sort_order == "desc":
        order_clauses = [order_col.desc().nullslast()]
    else:
        order_clauses = [order_col.asc().nullsfirst()]

    if is_new_expr is not None:
        order_clauses.insert(0, is_new_expr.desc())

    query = query.order_by(*order_clauses)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    papers = []
    for paper, assoc in items:
        is_new = (
            assoc.source == "track"
            and latest_track_start is not None
            and assoc.created_at is not None
            and assoc.created_at >= latest_track_start
        )
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
            influential_citation_count=paper.influential_citation_count or 0,
            impact_score=paper.impact_score or 0.0,
            is_survey=paper.is_survey or False,
            llm_score=assoc.llm_score,
            llm_reason=assoc.llm_reason,
            status=assoc.status or "inbox",
            source=assoc.source or "initialize",
            topic_id=assoc.ruleset_id,
            analysis=assoc.analysis,
            analyzed_at=assoc.analyzed_at,
            is_new=is_new,
        ))

    return PaperListResponse(total=total, page=page, page_size=page_size, items=papers)


@router.patch("/{ruleset_id}/papers/{paper_id}/status")
def update_paper_status(
    ruleset_id: int,
    paper_id: int,
    data: PaperStatusUpdate,
    db: Session = Depends(get_db),
):
    assoc = db.query(PaperRuleSet).filter(
        PaperRuleSet.paper_id == paper_id,
        PaperRuleSet.ruleset_id == ruleset_id,
    ).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="论文关联不存在")
    assoc.status = data.status
    db.commit()
    return {"message": "状态已更新"}


class BulkStatusUpdate(BaseModel):
    paper_ids: list[int] = Field(..., min_length=1)
    status: str = Field(..., pattern="^(inbox|archived|favorited)$")


@router.patch("/{ruleset_id}/papers/bulk-status")
def bulk_update_paper_status(
    ruleset_id: int,
    data: BulkStatusUpdate,
    db: Session = Depends(get_db),
):
    updated = db.query(PaperRuleSet).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.paper_id.in_(data.paper_ids),
    ).update({"status": data.status}, synchronize_session="fetch")
    db.commit()
    return {"message": f"{updated} 篇论文状态已更新", "updated": updated}


def _to_bibtex(paper: Paper) -> str:
    arxiv_id = paper.arxiv_id or ""
    if arxiv_id.startswith("s2:"):
        key = f"s2_{arxiv_id[3:]}"
    else:
        key = arxiv_id.replace(".", "_").replace("/", "_")

    authors_str = " and ".join(paper.authors or [])
    year = paper.year or ""
    lines = [
        f"@article{{{key},",
        f"  title={{{paper.title or ''}}},",
        f"  author={{{authors_str}}},",
        f"  year={{{year}}},",
    ]
    if paper.venue:
        lines.append(f"  journal={{{paper.venue}}},")
    if arxiv_id and not arxiv_id.startswith("s2:"):
        lines.append(f"  eprint={{{arxiv_id}}},")
        lines.append(f"  archiveprefix={{arXiv}},")
        lines.append(f"  url={{https://arxiv.org/abs/{arxiv_id}}},")
    lines.append("}")
    return "\n".join(lines)


S2_PAPER_FIELDS = (
    "paperId,externalIds,title,abstract,authors,year,"
    "citationCount,influentialCitationCount,venue,publicationVenue,"
    "publicationTypes,publicationDate"
)

_ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)


class AddPaperRequest(BaseModel):
    identifier: str = Field(..., min_length=1)


@router.post("/{ruleset_id}/papers/add")
async def add_paper_to_topic(
    ruleset_id: int,
    data: AddPaperRequest,
    db: Session = Depends(get_db),
):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    raw = data.identifier.strip()
    m = _ARXIV_RE.search(raw)
    arxiv_id = m.group(1) if m else None
    if not arxiv_id:
        raise HTTPException(status_code=400, detail="无法识别 ArXiv ID，请输入如 2501.12345 或 arxiv.org/abs/2501.12345")

    existing = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if existing:
        assoc = db.query(PaperRuleSet).filter(
            PaperRuleSet.paper_id == existing.id,
            PaperRuleSet.ruleset_id == ruleset_id,
        ).first()
        if assoc:
            assoc.status = "favorited"
            db.commit()
            return {"message": "论文已存在，已标记为收藏", "paper_id": existing.id}

    s2 = SemanticScholarService()
    s2_results = await s2.search_papers(query=f"arxiv:{arxiv_id}", limit=5, fields=S2_PAPER_FIELDS)

    s2_paper = None
    for r in s2_results:
        ext = r.get("externalIds") or {}
        if ext.get("ArXiv") == arxiv_id or ext.get("ArXiv") == arxiv_id.split("v")[0]:
            s2_paper = r
            break
    if not s2_paper and s2_results:
        s2_paper = s2_results[0]

    if not s2_paper:
        raise HTTPException(status_code=404, detail="Semantic Scholar 未收录该论文")

    ext_ids = s2_paper.get("externalIds") or {}
    pub_date = None
    if s2_paper.get("publicationDate"):
        try:
            pub_date = datetime.strptime(s2_paper["publicationDate"], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    authors = []
    for a in s2_paper.get("authors", []):
        if isinstance(a, dict) and "name" in a:
            authors.append(a["name"])

    paper = existing or Paper(
        arxiv_id=arxiv_id,
        s2_id=s2_paper.get("paperId"),
        title=s2_paper.get("title", ""),
        authors=authors,
        abstract=s2_paper.get("abstract"),
        categories=[],
        published_date=pub_date,
        year=s2_paper.get("year"),
        venue=s2_paper.get("venue"),
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        citation_count=s2_paper.get("citationCount", 0) or 0,
        influential_citation_count=s2_paper.get("influentialCitationCount", 0) or 0,
        impact_score=compute_impact_score(s2_paper),
        is_survey=is_survey_paper(s2_paper),
    )
    if not existing:
        db.add(paper)
        db.flush()

    assoc = PaperRuleSet(
        paper_id=paper.id,
        ruleset_id=ruleset_id,
        source="manual",
        status="favorited",
    )
    db.add(assoc)
    db.commit()

    return {"message": "论文已添加并收藏", "paper_id": paper.id, "title": paper.title}


@router.get("/{ruleset_id}/papers/bibtex")
def export_bibtex(
    ruleset_id: int,
    status: str = None,
    db: Session = Depends(get_db),
):
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")

    query = db.query(Paper).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(PaperRuleSet.ruleset_id == ruleset_id)

    if status:
        query = query.filter(PaperRuleSet.status == status)

    query = query.order_by(Paper.year.desc().nullslast())
    papers = query.all()

    bibtex = "\n\n".join(_to_bibtex(p) for p in papers)
    return PlainTextResponse(
        content=bibtex,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="{ruleset.name}_papers.bib"'},
    )


@router.get("/{ruleset_id}/papers/{paper_id}", response_model=PaperWithScore)
def get_paper_detail(
    ruleset_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
):
    row = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        Paper.id == paper_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="论文不存在")
    paper, assoc = row
    return PaperWithScore(
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
        influential_citation_count=paper.influential_citation_count or 0,
        impact_score=paper.impact_score or 0.0,
        is_survey=paper.is_survey or False,
        llm_score=assoc.llm_score,
        llm_reason=assoc.llm_reason,
        status=assoc.status or "inbox",
        source=assoc.source or "initialize",
        topic_id=assoc.ruleset_id,
        analysis=assoc.analysis,
        analyzed_at=assoc.analyzed_at,
    )


@router.post("/{ruleset_id}/papers/{paper_id}/analyze")
async def analyze_paper_endpoint(
    ruleset_id: int,
    paper_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from ..services.paper_analyzer import analyze_paper

    row = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        Paper.id == paper_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="论文不存在")
    paper, assoc = row

    paper_title = str(paper.title or "")[:60]
    task = create_task(
        "paper_analysis", f"Analyze: {paper_title}",
        ruleset_id=ruleset_id, paper_id=paper_id,
    )

    async def _run():
        from ..database import get_db_context
        try:
            result = await analyze_paper(
                arxiv_id=str(paper.arxiv_id),
                title=str(paper.title),
                authors=list(paper.authors or []),
                abstract=str(paper.abstract) if paper.abstract else None,
                year=int(paper.year) if paper.year else None,
                venue=str(paper.venue) if paper.venue else None,
                citation_count=int(paper.citation_count or 0),
            )
            with get_db_context() as db2:
                a = db2.query(PaperRuleSet).filter(
                    PaperRuleSet.paper_id == paper_id,
                    PaperRuleSet.ruleset_id == ruleset_id,
                ).first()
                if a:
                    a.analysis = result
                    a.analyzed_at = datetime.utcnow()
            complete_task(task.id)
        except Exception as e:
            fail_task(task.id, str(e))

    background_tasks.add_task(_run)
    return {"message": "分析已开始，请稍后刷新查看结果", "task_id": task.id}



