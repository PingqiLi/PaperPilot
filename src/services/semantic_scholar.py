"""
Semantic Scholar API 集成 - 获取论文引用数
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

from ..models import Paper
from ..database import get_db_context
from ..config import settings, rules_config

logger = structlog.get_logger(__name__)

# Semantic Scholar API
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"

class SemanticScholarService:
    """Semantic Scholar API 服务"""
    
    def __init__(self):
        self.api_key = settings.s2_api_key or rules_config.s2_api_key
        
        self.headers = {
            "User-Agent": "PaperAgent/1.0"
        }
        
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
            self.rate_limit_delay = 0.02  # 50 RPS (conservative for 100 limit)
        else:
            self.rate_limit_delay = 1.0   # 1 RPS (no key)
    
    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        通过ArXiv ID获取论文信息（包括引用数）
        """
        # 清理arxiv_id格式
        clean_id = arxiv_id.replace("v1", "").replace("v2", "").replace("v3", "")
        url = f"{S2_API_BASE}/paper/arXiv:{clean_id}"
        params = {"fields": "citationCount,influentialCitationCount,paperId"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                
                if response.status_code == 404:
                    logger.debug("Paper not found in S2", arxiv_id=arxiv_id)
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                return {
                    "semantic_scholar_id": data.get("paperId"),
                    "citation_count": data.get("citationCount", 0),
                    "influential_citations": data.get("influentialCitationCount", 0)
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("S2 rate limit hit, waiting...")
                await asyncio.sleep(1.0)
            return None
        except Exception as e:
            logger.error("S2 API error", arxiv_id=arxiv_id, error=str(e))
            return None
    
    async def get_citations_batch(self, arxiv_ids: List[str]) -> Dict[str, int]:
        """
        批量获取论文引用数（一次请求最多500篇）
        
        Returns:
            Dict[arxiv_id, citation_count]
        """
        if not arxiv_ids:
            return {}
        
        # 清理arxiv_id格式，构建S2 ID列表
        s2_ids = []
        id_map = {}  # S2格式 -> 原始格式
        for aid in arxiv_ids:
            clean_id = aid.replace("v1", "").replace("v2", "").replace("v3", "")
            # 跳过非ArXiv ID
            if clean_id.startswith("oa:") or clean_id.startswith("s2:"):
                continue
            s2_id = f"arXiv:{clean_id}"
            s2_ids.append(s2_id)
            id_map[s2_id] = aid
        
        if not s2_ids:
            return {}
        
        url = f"{S2_API_BASE}/paper/batch"
        params = {"fields": "citationCount,externalIds"}
        
        result = {}
        
        # 分批处理（每批最多500个）
        batch_size = 500
        for i in range(0, len(s2_ids), batch_size):
            batch = s2_ids[i:i+batch_size]
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        params=params,
                        headers=self.headers,
                        json={"ids": batch}
                    )
                    
                    if response.status_code == 429:
                        logger.warning("S2 batch API rate limited, waiting...")
                        await asyncio.sleep(5.0)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    for paper in data:
                        if paper is None:
                            continue
                        
                        # 提取原始ArXiv ID
                        external_ids = paper.get("externalIds", {}) or {}
                        arxiv = external_ids.get("ArXiv")
                        if arxiv:
                            result[arxiv] = paper.get("citationCount", 0)
                            # 同时尝试匹配带版本号的ID
                            for orig_id in id_map.values():
                                if arxiv in orig_id or orig_id in arxiv:
                                    result[orig_id] = paper.get("citationCount", 0)
                    
                    logger.info(
                        "S2 batch citations fetched",
                        requested=len(batch),
                        found=len([p for p in data if p])
                    )
                    
            except Exception as e:
                logger.error("S2 batch API error", error=str(e))
            
            # 批次间延迟
            await asyncio.sleep(1.0)
        
        return result
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_start: int = None,
        fields: str = None
    ) -> List[Dict[str, Any]]:
        """
        按关键词搜索高引用论文
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            year_start: 开始年份（只返回该年份之后的论文）
            fields: 需要的字段
            
        Returns:
            论文列表，按引用数降序
        """
        if fields is None:
            fields = "paperId,externalIds,title,abstract,authors,year,citationCount,venue,publicationDate"
        
        url = f"{S2_API_BASE}/paper/search"
        params = {
            "query": query,
            "limit": min(limit, 100),  # S2 API限制每次100
            "fields": fields,
        }
        
        if year_start:
            params["year"] = f"{year_start}-"
        
        all_papers = []
        offset = 0
        retry_count = 0
        max_retries = 3
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while len(all_papers) < limit:
                    params["offset"] = offset
                    
                    response = await client.get(url, params=params, headers=self.headers)
                    
                    if response.status_code == 429:
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.warning("S2 rate limit exceeded max retries, stopping")
                            break
                        wait_time = 5 * retry_count  # 指数退避：5s, 10s, 15s
                        logger.warning(f"S2 rate limit, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    retry_count = 0  # 成功后重置
                    response.raise_for_status()
                    data = response.json()
                    
                    papers = data.get("data", [])
                    if not papers:
                        break
                    
                    all_papers.extend(papers)
                    offset += len(papers)
                    
                    # 遵守速率限制 - 增加等待时间
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    if offset >= data.get("total", 0):
                        break
            
            # 按引用数排序
            all_papers.sort(key=lambda p: p.get("citationCount", 0) or 0, reverse=True)
            
            logger.info(
                "S2 search completed",
                query=query[:50],
                found=len(all_papers)
            )
            
            return all_papers[:limit]
            
        except Exception as e:
            logger.error("S2 search error", query=query, error=str(e))
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
        
        Args:
            keywords: 关键词列表
            semantic_query: 语义查询描述
            limit: 需要的论文数量
            year_start: 开始年份
            
        Returns:
            去重后的高引用论文列表
        """
        all_papers = {}
        
        # 用语义查询搜索
        if semantic_query:
            papers = await self.search_papers(
                query=semantic_query,
                limit=limit * 2,
                year_start=year_start
            )
            for p in papers:
                paper_id = p.get("paperId")
                if paper_id:
                    all_papers[paper_id] = p
        
        # 用关键词搜索
        for kw in keywords[:5]:  # 最多用5个主要关键词
            papers = await self.search_papers(
                query=kw,
                limit=limit,
                year_start=year_start
            )
            for p in papers:
                paper_id = p.get("paperId")
                if paper_id and paper_id not in all_papers:
                    all_papers[paper_id] = p
            
            await asyncio.sleep(self.rate_limit_delay)  # 避免速率限制
        
        # 按引用数排序，取Top K
        sorted_papers = sorted(
            all_papers.values(),
            key=lambda p: p.get("citationCount", 0) or 0,
            reverse=True
        )
        
        logger.info(
            "Classic papers collected",
            total_found=len(all_papers),
            returning=min(limit, len(sorted_papers))
        )
        
        return sorted_papers[:limit]
    
    async def batch_update_citations(
        self,
        paper_ids: List[int] = None,
        limit: int = 50,
        min_age_hours: int = 24
    ) -> int:
        """
        批量更新论文引用数
        
        Args:
            paper_ids: 指定论文ID列表，None则自动选择需要更新的
            limit: 最大更新数量
            min_age_hours: 距上次更新的最小时间间隔
        """
        updated = 0
        
        with get_db_context() as db:
            if paper_ids:
                papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
            else:
                # 选择从未更新或超过min_age_hours的论文
                cutoff = datetime.utcnow()
                papers = db.query(Paper).filter(
                    (Paper.citation_updated_at == None) |
                    (Paper.citation_updated_at < cutoff)
                ).limit(limit).all()
            
            for paper in papers:
                # 获取引用数
                result = await self.get_paper_by_arxiv_id(paper.arxiv_id)
                
                if result:
                    paper.citation_count = result["citation_count"]
                    paper.semantic_scholar_id = result["semantic_scholar_id"]
                    paper.citation_updated_at = datetime.utcnow()
                    updated += 1
                    
                    logger.debug(
                        "Citation updated",
                        paper_id=paper.id,
                        citations=result["citation_count"]
                    )
                
                # 遵守速率限制
                await asyncio.sleep(self.rate_limit_delay)
            
            db.commit()
        
        logger.info("Batch citation update completed", updated=updated)
        return updated


# 全局实例
semantic_scholar = SemanticScholarService()
