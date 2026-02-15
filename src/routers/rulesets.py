"""
规则集API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog

from ..database import get_db
from ..models import RuleSet, PaperRuleSet, Paper
from ..services.two_stage_filter import two_stage_filter
from ..services.semantic_scholar import semantic_scholar

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/rulesets", tags=["rulesets"])


# Pydantic schemas
class RuleSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    topic_description: Optional[str] = None  # 用于Agent筛选
    categories: List[str] = ["cs.AI", "cs.LG"]
    keywords_include: List[str] = []
    keywords_exclude: List[str] = []
    semantic_query: Optional[str] = None
    date_range_days: int = 30


class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    topic_description: Optional[str] = None
    categories: Optional[List[str]] = None
    keywords_include: Optional[List[str]] = None
    keywords_exclude: Optional[List[str]] = None
    semantic_query: Optional[str] = None
    date_range_days: Optional[int] = None
    is_active: Optional[bool] = None


class RuleSetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    topic_description: Optional[str]
    categories: List[str]
    keywords_include: List[str]
    keywords_exclude: List[str]
    semantic_query: Optional[str]
    date_range_days: int
    is_active: bool
    is_default: bool
    total_papers: int
    expanded_keywords: List[str]
    
    class Config:
        from_attributes = True


class PaperWithScore(BaseModel):
    id: int
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: Optional[str]
    categories: List[str]
    published_date: Optional[str]
    citation_count: int
    semantic_score: Optional[float]
    score_reason: Optional[str]
    
    class Config:
        from_attributes = True


# === 规则集 CRUD ===

@router.get("", response_model=List[RuleSetResponse])
def list_rulesets(db: Session = Depends(get_db)):
    """获取所有规则集"""
    rulesets = db.query(RuleSet).filter(RuleSet.is_active == True).all()
    return rulesets


@router.post("", response_model=RuleSetResponse)
def create_ruleset(data: RuleSetCreate, db: Session = Depends(get_db)):
    """创建新规则集"""
    # 检查名称唯一性
    existing = db.query(RuleSet).filter(RuleSet.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则集名称已存在")
    
    ruleset = RuleSet(**data.model_dump())
    db.add(ruleset)
    db.commit()
    db.refresh(ruleset)
    return ruleset


@router.get("/{ruleset_id}", response_model=RuleSetResponse)
def get_ruleset(ruleset_id: int, db: Session = Depends(get_db)):
    """获取单个规则集"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    return ruleset


@router.put("/{ruleset_id}", response_model=RuleSetResponse)
def update_ruleset(ruleset_id: int, data: RuleSetUpdate, db: Session = Depends(get_db)):
    """更新规则集"""
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
    """删除规则集（软删除）"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    ruleset.is_active = False
    db.commit()
    return {"message": "规则集已删除"}


# === 规则集论文操作 ===

@router.get("/{ruleset_id}/papers")
def get_ruleset_papers(
    ruleset_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "semantic_score",  # semantic_score, citation_count, published_date
    sort_order: str = "desc",
    min_score: float = 0,
    db: Session = Depends(get_db)
):
    """获取规则集下的论文列表"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 构建查询
    query = db.query(Paper, PaperRuleSet).join(
        PaperRuleSet, Paper.id == PaperRuleSet.paper_id
    ).filter(
        PaperRuleSet.ruleset_id == ruleset_id
    )
    
    # 分数过滤
    if min_score > 0:
        query = query.filter(PaperRuleSet.semantic_score >= min_score)
    
    # 排序
    if sort_by == "semantic_score":
        order_col = PaperRuleSet.semantic_score
    elif sort_by == "citation_count":
        order_col = Paper.citation_count
    else:
        order_col = Paper.published_date
    
    if sort_order == "desc":
        query = query.order_by(order_col.desc().nullslast())
    else:
        query = query.order_by(order_col.asc().nullsfirst())
    
    # 分页
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 格式化结果
    papers = []
    for paper, assoc in items:
        papers.append({
            "id": paper.id,
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": paper.authors or [],
            "abstract": paper.abstract,
            "categories": paper.categories or [],
            "published_date": paper.published_date.isoformat() if paper.published_date else None,
            "citation_count": paper.citation_count or 0,
            "semantic_score": assoc.semantic_score,
            "score_reason": assoc.score_reason,
            "is_scored": assoc.is_scored,
            "is_curated": assoc.is_curated,
            "is_new": assoc.is_new,
            "is_starred": paper.is_starred,
            "feedback": paper.feedback,
            "venue": paper.venue,
        })
    
    # 分区统计
    curated_papers = [p for p in papers if p.get("is_curated")]
    new_papers = [p for p in papers if p.get("is_new") and not p.get("is_curated")]
    
    return {
        "items": papers,
        "curated_papers": curated_papers,
        "new_papers": new_papers,
        "curated_count": len(curated_papers),
        "new_count": len(new_papers),
        "total": total,
        "page": page,
        "page_size": page_size,
        "ruleset_name": ruleset.name,
        "is_collected": ruleset.is_collected
    }


@router.get("/{ruleset_id}/stats")
def get_ruleset_stats(ruleset_id: int, db: Session = Depends(get_db)):
    """获取规则集统计信息（用于进度查询）"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 统计论文数量
    total_papers = db.query(PaperRuleSet).filter(
        PaperRuleSet.ruleset_id == ruleset_id
    ).count()
    
    scored_papers = db.query(PaperRuleSet).filter(
        PaperRuleSet.ruleset_id == ruleset_id,
        PaperRuleSet.is_scored == True
    ).count()
    
    return {
        "ruleset_id": ruleset_id,
        "name": ruleset.name,
        "total_papers": total_papers,
        "scored_papers": scored_papers,
        "last_fetch_at": ruleset.last_fetch_at.isoformat() if ruleset.last_fetch_at else None,
        "expanded_keywords": ruleset.expanded_keywords or []
    }


# === 后台任务 ===

@router.post("/{ruleset_id}/fetch")
async def trigger_fetch(
    ruleset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """触发规则集抓取（后台执行）"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 添加后台任务
    background_tasks.add_task(two_stage_filter.process_ruleset, ruleset)
    
    return {"message": f"规则集 '{ruleset.name}' 抓取任务已启动"}


@router.post("/{ruleset_id}/score")
async def trigger_scoring(
    ruleset_id: int,
    batch_size: int = 10,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """触发规则集语义评分（后台执行）"""
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 直接执行评分（小批量）
    scored = await two_stage_filter.batch_score_papers(
        ruleset_id=ruleset_id,
        batch_size=batch_size
    )
    
    return {"message": f"已评分 {scored} 篇论文"}


@router.post("/{ruleset_id}/update-citations")
async def update_citations(
    ruleset_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """更新规则集论文的引用数"""
    # 获取规则集下的论文ID
    paper_ids = [
        p.paper_id for p in 
        db.query(PaperRuleSet.paper_id).filter(
            PaperRuleSet.ruleset_id == ruleset_id
        ).limit(limit).all()
    ]
    
    updated = await semantic_scholar.batch_update_citations(paper_ids=paper_ids)
    
    return {"message": f"已更新 {updated} 篇论文的引用数"}


@router.post("/{ruleset_id}/collect")
async def trigger_collect(
    ruleset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    触发历史精选收集（Collect阶段）
    从过去N年的论文中筛选Top K高价值论文
    """
    from datetime import datetime
    
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    if ruleset.is_collected:
        return {"message": f"规则集 '{ruleset.name}' 已完成历史收集，如需重新收集请先重置"}
    
    # 后台执行收集任务
    background_tasks.add_task(
        _do_collect, 
        ruleset_id=ruleset_id,
        range_days=ruleset.collect_range_days,
        top_k=ruleset.collect_count
    )
    
    return {
        "message": f"开始收集 '{ruleset.name}' 的历史精选论文（过去{ruleset.collect_range_days}天，Top {ruleset.collect_count}）",
        "status": "collecting"
    }


@router.post("/{ruleset_id}/track")
async def trigger_track(
    ruleset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    触发追踪新论文（Track阶段）
    抓取最近N天的新论文
    """
    from datetime import datetime
    
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 后台执行追踪任务
    background_tasks.add_task(
        _do_track, 
        ruleset_id=ruleset_id,
        range_days=ruleset.track_range_days
    )
    
    return {
        "message": f"开始追踪 '{ruleset.name}' 的新论文（最近{ruleset.track_range_days}天）",
        "status": "tracking"
    }


@router.post("/{ruleset_id}/rapid-screening")
async def trigger_rapid_screening(
    ruleset_id: int,
    max_results: int = 20,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    触发快速主题筛选 (S2 + Agent)
    """
    ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="规则集不存在")
    
    # 后台执行
    background_tasks.add_task(
        two_stage_filter.rapid_screen_ruleset, 
        ruleset_id=ruleset_id,
        max_results=max_results
    )
    
    return {
        "message": f"开始对 '{ruleset.name}' 进行快速筛选 (S2 + Topic Description)",
        "status": "screening"
    }


# === 后台任务实现 ===

async def _do_collect(ruleset_id: int, range_days: int, top_k: int):
    """
    执行历史精选收集 (S2优先策略)
    策略：使用Semantic Scholar API直接搜索高引用论文
    """
    from datetime import datetime
    from ..database import SessionLocal
    from ..services.semantic_scholar import semantic_scholar
    
    db = SessionLocal()
    try:
        ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
        if not ruleset:
            return
        
        # Step 1: 使用S2收集经典论文

        s2_papers = await semantic_scholar.collect_classic_papers(
            keywords=ruleset.keywords_include or [],
            semantic_query=ruleset.semantic_query,
            limit=top_k * 2,  # 获取更多以防没有ArXiv ID
            year_start=datetime.now().year - (range_days // 365 + 1)
        )
        
        if not s2_papers:
            logger.warning("No papers found from S2", ruleset_id=ruleset_id)
            return
        
        # Step 2: 过滤并转换为Paper对象
        saved_count = 0
        for i, s2_paper in enumerate(s2_papers):

            # 必须有ArXiv ID
            external_ids = s2_paper.get("externalIds") or {}
            arxiv_id = external_ids.get("ArXiv")
            
            if not arxiv_id:
                continue

            
            # 停止条件
            if saved_count >= top_k:
                break
                
            # 检查论文是否已存在
            existing = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
            
            # 解析日期

            pub_date = None
            if s2_paper.get("publicationDate"):
                try:
                    pub_date = datetime.strptime(s2_paper.get("publicationDate"), "%Y-%m-%d")
                except:
                    pass
            
            # 作者列表处理
            authors = []
            for author in s2_paper.get("authors", []):
                if isinstance(author, dict) and "name" in author:
                    authors.append(author["name"])
                elif isinstance(author, str):
                    authors.append(author)
            
            if not existing:
                paper = Paper(
                    arxiv_id=arxiv_id,
                    title=s2_paper.get("title", ""),
                    authors=authors,
                    abstract=s2_paper.get("abstract", ""),
                    categories=ruleset.categories, # S2不提供ArXiv分类，暂用规则集分类兜底
                    published_date=pub_date,
                    pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    citation_count=s2_paper.get("citationCount", 0),
                    semantic_scholar_id=s2_paper.get("paperId"),
                    citation_updated_at=datetime.utcnow()
                )
                db.add(paper)
                db.flush()
            else:
                paper = existing
                # 更新引用数
                paper.citation_count = s2_paper.get("citationCount", 0)
                paper.semantic_scholar_id = s2_paper.get("paperId")
                paper.citation_updated_at = datetime.utcnow()
            
            # 创建关联
            existing_assoc = db.query(PaperRuleSet).filter(
                PaperRuleSet.paper_id == paper.id,
                PaperRuleSet.ruleset_id == ruleset_id
            ).first()
            
            if not existing_assoc:
                assoc = PaperRuleSet(
                    paper_id=paper.id,
                    ruleset_id=ruleset_id,
                    is_curated=True,
                    is_new=False,
                    is_scored=False
                )
                db.add(assoc)
                saved_count += 1
        
        # 更新规则集状态

        ruleset.is_collected = True
        ruleset.collected_at = datetime.utcnow()
        ruleset.curated_count = saved_count
        ruleset.total_papers = saved_count
        
        db.commit()
        logger.info("Collect completed (S2)", ruleset_id=ruleset_id, saved=saved_count)
        
    except Exception as e:
        import traceback
        traceback.print_exc() 
        logger.error("Collect failed", error=str(e))
        db.rollback()
    finally:
        db.close()


async def _do_track(ruleset_id: int, range_days: int):
    """执行追踪新论文"""
    from datetime import datetime
    from ..database import SessionLocal
    
    db = SessionLocal()
    try:
        ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
        if not ruleset:
            return
        
        # 保存原始时间范围
        original_range = ruleset.date_range_days
        ruleset.date_range_days = range_days
        
        # 记录当前论文ID
        existing_ids = set(
            p.paper_id for p in 
            db.query(PaperRuleSet.paper_id).filter(
                PaperRuleSet.ruleset_id == ruleset_id
            ).all()
        )
        
        await two_stage_filter.process_ruleset(ruleset)
        
        # 标记新抓取的论文
        new_associations = db.query(PaperRuleSet).filter(
            PaperRuleSet.ruleset_id == ruleset_id,
            ~PaperRuleSet.paper_id.in_(existing_ids) if existing_ids else True
        ).all()
        
        for assoc in new_associations:
            assoc.is_new = True
            assoc.is_curated = False
        
        # 更新规则集状态
        ruleset.date_range_days = original_range
        ruleset.last_track_at = datetime.utcnow()
        ruleset.new_count = len(new_associations)
        
        db.commit()
    finally:
        db.close()
