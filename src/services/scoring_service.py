"""
综合评分服务 - 语义分 + 引用分加权
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import structlog

from ..models import Paper, PaperRuleSet, RuleSet
from ..database import get_db_context

logger = structlog.get_logger(__name__)


class ScoringService:
    """综合评分服务"""
    
    # 权重配置
    SEMANTIC_WEIGHT = 0.7
    CITATION_WEIGHT = 0.3
    
    # 二次时间衰减系数 β（按天）
    # 使用较小的值使衰减更平缓：1 + β × days²
    TIME_DECAY_BETA = 0.00001
    
    def calculate_days_since_publish(self, publish_date: datetime) -> int:
        """计算发表天数"""
        if not publish_date:
            return 180  # 默认半年
        
        delta = datetime.utcnow() - publish_date
        return max(1, delta.days)
    
    def calculate_quadratic_decay(self, days: int) -> float:
        """
        二次时间衰减（AI领域强调时效性）
        decay_factor = 1 + β × days²
        """
        return 1 + self.TIME_DECAY_BETA * (days ** 2)
    
    def calculate_velocity_bonus(
        self, 
        citation_count: int, 
        days: int
    ) -> float:
        """
        引用增长速度奖励
        bonus = 1 + log(1 + citations_per_day × 100)
        
        低成本近似：日均引用作为增长速度指标
        """
        import math
        citations_per_day = citation_count / max(days, 1)
        return 1 + math.log(1 + citations_per_day * 100)
    
    def calculate_velocity_score(
        self, 
        citation_count: int, 
        publish_date: datetime
    ) -> float:
        """
        计算速度得分（综合衰减和增长速度）
        velocity_score = adjusted_citations × velocity_bonus
        """
        days = self.calculate_days_since_publish(publish_date)
        
        # 二次时间衰减
        decay_factor = self.calculate_quadratic_decay(days)
        adjusted_citations = citation_count / decay_factor
        
        # 增长速度奖励
        velocity_bonus = self.calculate_velocity_bonus(citation_count, days)
        
        return adjusted_citations * velocity_bonus
    
    def calculate_percentile_score(
        self,
        velocity_score: float,
        all_velocity_scores: List[float]
    ) -> float:
        """
        计算百分位得分 (0-10)
        在RuleSet内排名的百分位 × 10
        """
        if not all_velocity_scores:
            return 5.0  # 无数据时默认中等分
        
        sorted_values = sorted(all_velocity_scores)
        n = len(sorted_values)
        
        # 找到当前值的排名
        rank = sum(1 for v in sorted_values if v <= velocity_score)
        percentile = rank / n
        
        return percentile * 10
    
    def calculate_combined_score(
        self,
        semantic_score: float,
        citation_percentile: float
    ) -> float:
        """
        计算综合得分
        combined = 0.7 × semantic + 0.3 × citation_percentile
        """
        semantic = semantic_score or 5.0
        citation = citation_percentile or 5.0
        
        return (
            self.SEMANTIC_WEIGHT * semantic + 
            self.CITATION_WEIGHT * citation
        )
    
    def update_ruleset_scores(self, ruleset_id: int) -> int:
        """
        更新规则集内所有论文的综合评分
        """
        updated = 0
        
        with get_db_context() as db:
            # 获取规则集内所有论文的调整后引用数
            associations = db.query(PaperRuleSet, Paper).join(
                Paper, PaperRuleSet.paper_id == Paper.id
            ).filter(
                PaperRuleSet.ruleset_id == ruleset_id
            ).all()
            
            if not associations:
                return 0
            
            # 计算所有论文的调整后引用数
            adjusted_citations_list = []
            paper_adjusted = {}
            
            for assoc, paper in associations:
                adjusted = self.calculate_adjusted_citations(
                    paper.citation_count or 0,
                    paper.published_date
                )
                adjusted_citations_list.append(adjusted)
                paper_adjusted[paper.id] = adjusted
            
            # 计算每篇论文的百分位得分和综合得分
            for assoc, paper in associations:
                adjusted = paper_adjusted[paper.id]
                citation_score = self.calculate_percentile_score(
                    adjusted, adjusted_citations_list
                )
                
                # 更新综合得分（存储在PaperRuleSet中）
                if assoc.semantic_score is not None:
                    combined = self.calculate_combined_score(
                        assoc.semantic_score,
                        citation_score
                    )
                    # 我们可以额外存储这些信息
                    # 暂时将综合分存入score_reason的JSON中
                    assoc.score_reason = (
                        f"语义:{assoc.semantic_score:.1f} "
                        f"引用百分位:{citation_score:.1f} "
                        f"综合:{combined:.1f}"
                    )
                    updated += 1
            
            db.commit()
        
        logger.info("RuleSet scores updated", ruleset_id=ruleset_id, updated=updated)
        return updated
    
    def get_papers_sorted_by_combined(
        self,
        db: Session,
        ruleset_id: int,
        limit: int = 50
    ) -> List[Tuple[Paper, PaperRuleSet, float]]:
        """
        获取按综合得分排序的论文
        """
        associations = db.query(PaperRuleSet, Paper).join(
            Paper, PaperRuleSet.paper_id == Paper.id
        ).filter(
            PaperRuleSet.ruleset_id == ruleset_id,
            PaperRuleSet.is_scored == True
        ).all()
        
        if not associations:
            return []
        
        # 计算调整后引用
        adjusted_list = []
        for assoc, paper in associations:
            adjusted = self.calculate_adjusted_citations(
                paper.citation_count or 0,
                paper.published_date
            )
            adjusted_list.append((assoc, paper, adjusted))
        
        all_adjusted = [a[2] for a in adjusted_list]
        
        # 计算综合得分并排序
        results = []
        for assoc, paper, adjusted in adjusted_list:
            citation_score = self.calculate_percentile_score(adjusted, all_adjusted)
            combined = self.calculate_combined_score(
                assoc.semantic_score or 5.0,
                citation_score
            )
            results.append((paper, assoc, combined))
        
        # 按综合得分降序排序
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]


# 全局实例
scoring_service = ScoringService()
