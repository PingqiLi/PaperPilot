"""
OpenAlex API 集成 - 免费获取论文引用数据
https://docs.openalex.org/
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

logger = structlog.get_logger(__name__)

# OpenAlex API
OPENALEX_API = "https://api.openalex.org"


class OpenAlexService:
    """OpenAlex API 服务 - 免费无限制"""
    
    def __init__(self, email: str = None):
        """
        Args:
            email: 可选，提供邮箱可获得更高速率限制（推荐）
        """
        self.headers = {
            "User-Agent": "PaperAgent/1.0 (https://github.com/paper-agent)"
        }
        if email:
            self.headers["mailto"] = email
    
    async def search_papers(
        self,
        query: str,
        limit: int = 50,
        year_start: int = None,
        sort_by: str = "cited_by_count:desc"
    ) -> List[Dict[str, Any]]:
        """
        搜索论文，默认按引用数降序
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            year_start: 开始年份
            sort_by: 排序方式
        """
        url = f"{OPENALEX_API}/works"
        params = {
            "search": query,
            "per_page": min(limit, 200),  # OpenAlex最多200条
            "sort": sort_by,
            "select": "id,doi,title,display_name,publication_year,publication_date,cited_by_count,authorships,primary_location,concepts"
        }
        
        if year_start:
            params["filter"] = f"publication_year:>{year_start-1}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for work in data.get("results", []):
                    # 提取ArXiv ID
                    arxiv_id = None
                    location = work.get("primary_location", {}) or {}
                    landing_url = location.get("landing_page_url", "") or ""
                    if "arxiv.org" in landing_url:
                        arxiv_id = landing_url.split("/")[-1]
                    
                    # 提取作者
                    authors = []
                    affiliations = []
                    for auth in work.get("authorships", [])[:10]:
                        author = auth.get("author", {}) or {}
                        authors.append(author.get("display_name", ""))
                        
                        # 提取机构
                        for inst in auth.get("institutions", [])[:1]:
                            affiliations.append(inst.get("display_name", ""))
                    
                    # 提取发表信息
                    source = location.get("source", {}) or {}
                    venue = source.get("display_name")
                    
                    papers.append({
                        "openalex_id": work.get("id"),
                        "arxiv_id": arxiv_id,
                        "doi": work.get("doi"),
                        "title": work.get("title") or work.get("display_name"),
                        "authors": authors,
                        "affiliations": list(set(affiliations)),
                        "publication_year": work.get("publication_year"),
                        "publication_date": work.get("publication_date"),
                        "cited_by_count": work.get("cited_by_count", 0),
                        "venue": venue,
                        "pdf_url": location.get("pdf_url"),
                    })
                
                logger.info(
                    "OpenAlex search completed",
                    query=query[:50],
                    found=len(papers)
                )
                return papers
                
        except Exception as e:
            logger.error("OpenAlex API error", error=str(e))
            return []
    
    async def collect_classic_papers(
        self,
        keywords: List[str],
        semantic_query: str = None,
        limit: int = 50,
        year_start: int = 2021
    ) -> List[Dict[str, Any]]:
        """
        收集经典论文（用于Collect阶段）
        使用OpenAlex按引用数搜索高质量论文，并过滤确保相关性
        """
        all_papers = {}
        
        # 构建更精确的组合查询：关键词 AND/OR 组合
        if keywords:
            # 方案1：用核心关键词组合搜索（更精准）
            core_keywords = keywords[:5]  # 取前5个核心关键词
            combined_query = " ".join(core_keywords)  # OpenAlex默认AND
            
            papers = await self.search_papers(
                query=combined_query,
                limit=limit * 3,  # 搜索更多，后面会过滤
                year_start=year_start
            )
            
            for p in papers:
                key = p.get("openalex_id") or p.get("title")
                if key:
                    all_papers[key] = p
        
        # 如果组合搜索结果不够，用单个关键词补充
        if len(all_papers) < limit:
            for kw in keywords[:3]:
                papers = await self.search_papers(
                    query=kw,
                    limit=limit,
                    year_start=year_start
                )
                for p in papers:
                    key = p.get("openalex_id") or p.get("title")
                    if key and key not in all_papers:
                        all_papers[key] = p
                
                await asyncio.sleep(0.2)
        
        # 关键词过滤：确保论文标题包含至少一个关键词
        def contains_keyword(paper: Dict) -> bool:
            title = (paper.get("title") or "").lower()
            # 检查是否包含任一关键词
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in title:
                    return True
            return False
        
        # 过滤并按引用数排序
        filtered_papers = [p for p in all_papers.values() if contains_keyword(p)]
        
        # 如果过滤后太少，放宽条件（至少保留一半）
        if len(filtered_papers) < limit // 2:
            logger.warning(
                "Keyword filter too strict, relaxing",
                before=len(all_papers),
                after=len(filtered_papers)
            )
            # 按引用数排序所有结果
            filtered_papers = list(all_papers.values())
        
        sorted_papers = sorted(
            filtered_papers,
            key=lambda p: p.get("cited_by_count", 0) or 0,
            reverse=True
        )
        
        logger.info(
            "OpenAlex classic papers collected",
            total_found=len(all_papers),
            after_filter=len(filtered_papers),
            returning=min(limit, len(sorted_papers))
        )
        
        return sorted_papers[:limit]
    
    async def get_paper_citations(self, arxiv_id: str) -> Optional[int]:
        """通过ArXiv ID获取论文引用数"""
        url = f"{OPENALEX_API}/works"
        params = {
            "filter": f"locations.landing_page_url.search:arxiv.org/abs/{arxiv_id}",
            "select": "cited_by_count"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if results:
                    return results[0].get("cited_by_count", 0)
                return None
                
        except Exception as e:
            logger.debug("OpenAlex citation lookup failed", arxiv_id=arxiv_id, error=str(e))
            return None


# 全局实例
openalex = OpenAlexService()
