"""
论文API路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..schemas.paper import (
    PaperListResponse, PaperDetail, PaperUpdate, PaperSummary, FetchStatus
)
from ..database import get_db

router = APIRouter()


@router.get("", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    starred_only: bool = False,
    unread_only: bool = False,
    search: Optional[str] = None,
    sort_by: str = Query("published_date", regex="^(published_date|relevance_score|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    获取论文列表
    
    - **page**: 页码
    - **page_size**: 每页数量
    - **category**: 按分类筛选
    - **min_score**: 最低评分筛选
    - **starred_only**: 只显示收藏
    - **unread_only**: 只显示未读
    - **search**: 搜索标题和摘要
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向
    """
    from ..models.paper import Paper
    
    query = db.query(Paper)
    
    # 应用筛选条件
    if category:
        query = query.filter(Paper.categories.contains([category]))
    if min_score is not None:
        query = query.filter(Paper.relevance_score >= min_score)
    if starred_only:
        query = query.filter(Paper.is_starred == True)
    if unread_only:
        query = query.filter(Paper.is_read == False)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Paper.title.ilike(search_term)) | 
            (Paper.abstract.ilike(search_term))
        )
    
    # 排序
    order_column = getattr(Paper, sort_by)
    if sort_order == "desc":
        order_column = order_column.desc()
    query = query.order_by(order_column)
    
    # 分页
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaperListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[PaperSummary.model_validate(p) for p in items]
    )


@router.get("/status", response_model=FetchStatus)
async def get_fetch_status(db: Session = Depends(get_db)):
    """获取抓取状态"""
    from ..models.paper import Paper, FetchLog
    from datetime import datetime, timedelta
    
    # 获取最后一次抓取记录
    last_log = db.query(FetchLog).order_by(FetchLog.fetch_time.desc()).first()
    
    # 统计
    total_papers = db.query(Paper).count()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    papers_today = db.query(Paper).filter(Paper.created_at >= today_start).count()
    
    return FetchStatus(
        last_fetch=last_log.fetch_time if last_log else None,
        next_fetch=None,  # TODO: 从调度器获取
        total_papers=total_papers,
        papers_today=papers_today
    )


@router.get("/{paper_id}", response_model=PaperDetail)
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """获取论文详情"""
    from ..models.paper import Paper
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return PaperDetail.model_validate(paper)


@router.patch("/{paper_id}", response_model=PaperDetail)
async def update_paper(
    paper_id: int, 
    update: PaperUpdate,
    db: Session = Depends(get_db)
):
    """更新论文（收藏、已读、笔记）"""
    from ..models.paper import Paper
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(paper, key, value)
    
    db.commit()
    db.refresh(paper)
    
    return PaperDetail.model_validate(paper)


@router.post("/{paper_id}/process")
async def process_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    手动触发论文处理（PDF解析 + LLM工作流）
    """
    from ..models.paper import Paper
    from ..services.paper_processor import process_single_paper
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 异步处理
    await process_single_paper(paper, db)
    
    db.refresh(paper)
    return {"status": "processed", "paper_id": paper_id}


@router.post("/fetch")
async def trigger_fetch(db: Session = Depends(get_db)):
    """手动触发抓取"""
    from ..services.arxiv_fetcher import fetch_papers
    
    result = await fetch_papers()
    return {
        "status": "completed",
        "fetched": result.get("fetched", 0),
        "filtered": result.get("filtered", 0)
    }
