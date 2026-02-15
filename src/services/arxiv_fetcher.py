"""
ArXiv论文抓取服务
"""
import arxiv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog

from ..config import rules_config
from ..database import get_db_context
from ..models.paper import Paper, FetchLog

logger = structlog.get_logger(__name__)


class ArxivFetcher:
    """ArXiv论文抓取器"""
    
    def __init__(self):
        self.client = arxiv.Client()
    
    def build_query(
        self,
        categories: List[str],
        keywords_include: List[str] = None,
        keywords_exclude: List[str] = None,
        date_range: int = 7
    ) -> str:
        """
        构建ArXiv查询字符串
        
        Args:
            categories: ArXiv分类列表，如 ["cs.AI", "cs.LG"]
            keywords_include: 包含的关键词
            keywords_exclude: 排除的关键词
            date_range: 查询最近N天
        
        Returns:
            ArXiv查询字符串
        """
        # 分类查询
        cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
        query_parts = [f"({cat_query})"]
        
        # 关键词包含
        if keywords_include:
            kw_include = " OR ".join([f'"{kw}"' for kw in keywords_include])
            query_parts.append(f"({kw_include})")
        
        # 关键词排除
        if keywords_exclude:
            kw_exclude = " AND ".join([f'NOT "{kw}"' for kw in keywords_exclude])
            query_parts.append(f"({kw_exclude})")
        
        return " AND ".join(query_parts)
    
    def fetch(
        self,
        categories: List[str],
        keywords_include: List[str] = None,
        keywords_exclude: List[str] = None,
        max_results: int = 100,
        date_range: int = 7
    ) -> List[Dict[str, Any]]:
        """
        抓取论文
        
        Returns:
            论文列表，每个论文是一个字典
        """
        query = self.build_query(
            categories, 
            keywords_include, 
            keywords_exclude,
            date_range
        )
        
        logger.info("Fetching papers from ArXiv", query=query, max_results=max_results)
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        papers = []
        cutoff_date = datetime.now() - timedelta(days=date_range)
        
        for result in self.client.results(search):
            # 日期过滤
            if result.published.replace(tzinfo=None) < cutoff_date:
                continue
            
            paper = {
                "arxiv_id": result.entry_id.split("/")[-1],
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary,
                "categories": result.categories,
                "published_date": result.published,
                "updated_date": result.updated,
                "pdf_url": result.pdf_url
            }
            papers.append(paper)
        
        logger.info("Fetched papers", count=len(papers))
        return papers
    
    def filter_by_keywords(
        self,
        papers: List[Dict[str, Any]],
        keywords_include: List[str],
        keywords_exclude: List[str]
    ) -> List[Dict[str, Any]]:
        """
        本地关键词过滤（补充ArXiv API的限制）
        """
        filtered = []
        
        for paper in papers:
            text = f"{paper['title']} {paper['abstract']}".lower()
            
            # 检查包含关键词
            if keywords_include:
                if not any(kw.lower() in text for kw in keywords_include):
                    continue
            
            # 检查排除关键词
            if keywords_exclude:
                if any(kw.lower() in text for kw in keywords_exclude):
                    continue
            
            filtered.append(paper)
        
        return filtered


async def fetch_papers() -> Dict[str, int]:
    """
    执行论文抓取任务
    
    Returns:
        抓取结果统计
    """
    fetcher = ArxivFetcher()
    start_time = datetime.utcnow()
    
    # 从配置加载规则
    categories = rules_config.categories
    keywords_include = rules_config.keywords_include
    keywords_exclude = rules_config.keywords_exclude
    config = rules_config.load()
    max_results = config.get("rules", {}).get("advanced", {}).get("max_papers_per_fetch", 100)
    date_range = config.get("rules", {}).get("date_range", 7)
    
    if not categories:
        logger.warning("No categories configured, skipping fetch")
        return {"fetched": 0, "filtered": 0, "saved": 0}
    
    # 抓取论文（只用分类查询，不传关键词到ArXiv API避免查询过于复杂）
    papers = fetcher.fetch(
        categories=categories,
        keywords_include=None,  # 不传到API
        keywords_exclude=None,  # 不传到API
        max_results=max_results,
        date_range=date_range
    )
    
    # 本地关键词过滤（这样更可靠）
    filtered_papers = fetcher.filter_by_keywords(
        papers, keywords_include or [], keywords_exclude or []
    )
    
    # 保存到数据库
    saved_count = 0
    with get_db_context() as db:
        for paper_data in filtered_papers:
            # 检查是否已存在
            existing = db.query(Paper).filter(
                Paper.arxiv_id == paper_data["arxiv_id"]
            ).first()
            
            if not existing:
                paper = Paper(**paper_data)
                db.add(paper)
                saved_count += 1
        
        # 记录抓取日志
        duration = (datetime.utcnow() - start_time).total_seconds()
        fetch_log = FetchLog(
            categories=categories,
            total_fetched=len(papers),
            total_filtered=len(filtered_papers),
            status="completed",
            duration_seconds=duration
        )
        db.add(fetch_log)
    
    logger.info(
        "Fetch completed",
        fetched=len(papers),
        filtered=len(filtered_papers),
        saved=saved_count
    )
    
    return {
        "fetched": len(papers),
        "filtered": len(filtered_papers),
        "saved": saved_count
    }


def search_by_relevance(
    keywords: List[str],
    semantic_query: str = None,
    max_results: int = 100,
    categories: List[str] = None
) -> List[Dict[str, Any]]:
    """
    按相关度搜索ArXiv论文（用于Collect阶段）
    策略：对每个核心关键词分开搜索，然后合并去重
    """
    all_papers = {}
    client = arxiv.Client()
    
    # 定义核心方法名（必须搜索的）
    core_methods = ["GPTQ", "AWQ", "SmoothQuant", "ZeroQuant", "LLM.int8", "SpinQuant", "QuaRot"]
    
    # 从keywords中提取核心方法名和普通关键词
    method_keywords = [kw for kw in keywords if kw in core_methods]
    general_keywords = [kw for kw in keywords if kw not in core_methods][:5]
    
    # Step 1: 对每个核心方法名单独搜索（确保经典论文不遗漏）
    for method in method_keywords:
        query = f'ti:"{method}"'  # 在标题中搜索
        
        logger.info(f"Searching ArXiv for method: {method}")
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=20,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/")[-1]
                if arxiv_id not in all_papers:
                    all_papers[arxiv_id] = {
                        "arxiv_id": arxiv_id,
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "abstract": result.summary,
                        "categories": result.categories,
                        "published_date": result.published,
                        "updated_date": result.updated,
                        "pdf_url": result.pdf_url
                    }
        except Exception as e:
            logger.error(f"ArXiv search error for {method}", error=str(e))
    
    # Step 2: 用普通关键词组合搜索补充
    if general_keywords and len(all_papers) < max_results:
        kw_query = " OR ".join([f'all:"{kw}"' for kw in general_keywords])
        
        # 加分类限制
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({kw_query}) AND ({cat_query})"
        else:
            query = kw_query
        
        logger.info("Searching ArXiv with general keywords", query=query[:80])
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/")[-1]
                if arxiv_id not in all_papers:
                    all_papers[arxiv_id] = {
                        "arxiv_id": arxiv_id,
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "abstract": result.summary,
                        "categories": result.categories,
                        "published_date": result.published,
                        "updated_date": result.updated,
                        "pdf_url": result.pdf_url
                    }
        except Exception as e:
            logger.error("ArXiv general search error", error=str(e))
    
    papers = list(all_papers.values())
    logger.info(f"ArXiv search completed, found {len(papers)} unique papers")
    
    return papers[:max_results]
