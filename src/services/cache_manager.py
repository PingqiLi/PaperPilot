"""
缓存管理服务 - 控制论文缓存空间
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
import structlog

from ..models import Paper, PaperRuleSet
from ..database import get_db_context

logger = structlog.get_logger(__name__)


class CacheManager:
    """论文缓存管理器"""
    
    # 默认配置
    MAX_PAPERS = 50000          # 最大缓存论文数
    MAX_STORAGE_MB = 500        # 最大存储空间（估算）
    BYTES_PER_PAPER = 5000      # 每篇论文约5KB
    
    def __init__(
        self,
        max_papers: int = None,
        max_storage_mb: int = None
    ):
        self.max_papers = max_papers or self.MAX_PAPERS
        self.max_storage_mb = max_storage_mb or self.MAX_STORAGE_MB
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        with get_db_context() as db:
            total_papers = db.query(func.count(Paper.id)).scalar()
            
            # 估算存储空间
            estimated_mb = (total_papers * self.BYTES_PER_PAPER) / (1024 * 1024)
            
            # 最老/最新论文日期
            oldest = db.query(func.min(Paper.created_at)).scalar()
            newest = db.query(func.max(Paper.created_at)).scalar()
            
            return {
                "total_papers": total_papers,
                "estimated_mb": round(estimated_mb, 2),
                "max_papers": self.max_papers,
                "max_storage_mb": self.max_storage_mb,
                "usage_percent": round(total_papers / self.max_papers * 100, 1),
                "oldest_entry": oldest.isoformat() if oldest else None,
                "newest_entry": newest.isoformat() if newest else None
            }
    
    def needs_eviction(self) -> bool:
        """检查是否需要淘汰"""
        stats = self.get_cache_stats()
        return (
            stats["total_papers"] >= self.max_papers or
            stats["estimated_mb"] >= self.max_storage_mb
        )
    
    def evict_lru(self, count: int = 1000) -> int:
        """
        淘汰最近最少使用的论文
        LRU策略：按created_at + 无关联规则集 优先淘汰
        """
        evicted = 0
        
        with get_db_context() as db:
            # 找到没有任何规则集关联的旧论文
            orphan_papers = db.query(Paper).outerjoin(
                PaperRuleSet, Paper.id == PaperRuleSet.paper_id
            ).filter(
                PaperRuleSet.id == None
            ).order_by(
                Paper.created_at.asc()
            ).limit(count).all()
            
            for paper in orphan_papers:
                db.delete(paper)
                evicted += 1
            
            # 如果还需要淘汰更多
            remaining = count - evicted
            if remaining > 0 and self.needs_eviction():
                # 淘汰低分论文
                low_score_assocs = db.query(PaperRuleSet).filter(
                    PaperRuleSet.semantic_score < 4.0
                ).order_by(
                    PaperRuleSet.semantic_score.asc()
                ).limit(remaining).all()
                
                for assoc in low_score_assocs:
                    paper = db.query(Paper).filter(Paper.id == assoc.paper_id).first()
                    # 检查是否只属于一个规则集
                    assoc_count = db.query(func.count(PaperRuleSet.id)).filter(
                        PaperRuleSet.paper_id == assoc.paper_id
                    ).scalar()
                    
                    if assoc_count == 1 and paper:
                        db.delete(assoc)
                        db.delete(paper)
                        evicted += 1
            
            db.commit()
        
        logger.info("Cache eviction completed", evicted=evicted)
        return evicted
    
    def auto_evict_if_needed(self) -> int:
        """自动检查并淘汰"""
        if self.needs_eviction():
            return self.evict_lru()
        return 0


# 全局实例
cache_manager = CacheManager()
