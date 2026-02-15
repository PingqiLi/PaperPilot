"""
论文处理服务 - 协调PDF解析和LLM工作流
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
import structlog

from ..models.paper import Paper
from ..database import get_db_context
from ..config import rules_config
from .pdf_parser import get_pdf_parser, get_simple_parser
# from .llm_service import llm_service  # Removed
from .openclaw_service import openclaw_client
from ..workflows.rating import RatingWorkflow
from ..workflows.summarization import SummarizationWorkflow
from ..workflows.extraction import ExtractionWorkflow

logger = structlog.get_logger(__name__)


async def process_single_paper(paper: Paper, db: Session) -> bool:
    """
    处理单篇论文
    
    流程：
    1. 下载并解析PDF为Markdown
    2. 运行评分工作流
    3. 运行摘要工作流
    4. 运行信息抽取工作流
    5. 保存结果
    """
    logger.info("Processing paper", arxiv_id=paper.arxiv_id, title=paper.title[:50])
    
    try:
        # 1. 解析PDF
        if paper.pdf_url and not paper.markdown_content:
            parser = get_pdf_parser()
            markdown = await parser.parse_from_url(paper.pdf_url)
            
            if not markdown:
                # 降级到简单解析
                simple_parser = get_simple_parser()
                markdown = await simple_parser.parse_from_url(paper.pdf_url)
            
            if markdown:
                paper.markdown_content = markdown
                logger.info("PDF parsed", arxiv_id=paper.arxiv_id)
        
        # 获取用户兴趣描述
        interests = rules_config.interests
        
        # 2. 评分工作流
        rating_workflow = RatingWorkflow(openclaw_client)
        rating_result = await rating_workflow.run(
            title=paper.title,
            abstract=paper.abstract,
            interests=interests
        )
        paper.relevance_score = rating_result.get("score")
        paper.score_reason = rating_result.get("reason")
        logger.info(
            "Rating completed",
            arxiv_id=paper.arxiv_id,
            score=paper.relevance_score
        )
        
        # 3. 摘要工作流（使用Markdown全文或摘要）
        content = paper.markdown_content or paper.abstract
        if content:
            summary_workflow = SummarizationWorkflow(openclaw_client)
            summary_result = await summary_workflow.run(content=content)
            paper.summary = summary_result.get("summary")
            paper.key_findings = summary_result.get("key_findings", [])
            paper.methodology = summary_result.get("methodology")
        
        # 4. 抽取工作流
        extraction_workflow = ExtractionWorkflow(openclaw_client)
        extraction_result = await extraction_workflow.run(
            title=paper.title,
            abstract=paper.abstract,
            content=paper.markdown_content
        )
        paper.extracted_info = extraction_result
        
        # 5. 标记为已处理
        paper.is_processed = True
        db.commit()
        
        logger.info("Paper processed", arxiv_id=paper.arxiv_id)
        return True
        
    except Exception as e:
        logger.error(
            "Paper processing failed",
            arxiv_id=paper.arxiv_id,
            error=str(e)
        )
        db.rollback()
        return False


async def process_unprocessed_papers(
    limit: int = 50,
    min_score: float = None
) -> Dict[str, int]:
    """
    批量处理未处理的论文
    
    Args:
        limit: 最大处理数量
        min_score: 只处理评分高于此值的论文（需先完成评分）
    
    Returns:
        处理统计
    """
    processed = 0
    failed = 0
    skipped = 0
    
    score_threshold = rules_config.score_threshold
    
    with get_db_context() as db:
        # 查询未处理的论文
        query = db.query(Paper).filter(Paper.is_processed == False)
        
        # 如果设置了评分阈值，优先处理高分论文
        if min_score is not None:
            query = query.filter(Paper.relevance_score >= min_score)
        
        papers = query.order_by(Paper.created_at.desc()).limit(limit).all()
        
        for paper in papers:
            # 如果已有评分但低于阈值，跳过后续处理
            if paper.relevance_score and paper.relevance_score < score_threshold:
                paper.is_processed = True  # 标记为已处理但跳过详细分析
                skipped += 1
                continue
            
            success = await process_single_paper(paper, db)
            if success:
                processed += 1
            else:
                failed += 1
    
    return {
        "processed": processed,
        "failed": failed,
        "skipped": skipped
    }


async def rate_papers_only(limit: int = 100) -> Dict[str, int]:
    """
    只进行评分（快速筛选阶段）
    
    用于两阶段筛选：先快速评分，再详细处理高分论文
    """
    rated = 0
    failed = 0
    
    interests = rules_config.interests
    rating_workflow = RatingWorkflow(openclaw_client)
    
    with get_db_context() as db:
        # 查询未评分的论文
        papers = db.query(Paper).filter(
            Paper.relevance_score == None
        ).order_by(Paper.created_at.desc()).limit(limit).all()
        
        for paper in papers:
            try:
                result = await rating_workflow.run(
                    title=paper.title,
                    abstract=paper.abstract,
                    interests=interests
                )
                paper.relevance_score = result.get("score")
                paper.score_reason = result.get("reason")
                db.commit()
                rated += 1
            except Exception as e:
                logger.error("Rating failed", arxiv_id=paper.arxiv_id, error=str(e))
                failed += 1
    
    return {"rated": rated, "failed": failed}
