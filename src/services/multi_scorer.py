"""
多维度评分服务 - 综合语义、引用、机构、发表四个维度
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import math
import re
import structlog

logger = structlog.get_logger(__name__)


# 顶级实验室/机构评分
TOP_LABS = {
    # 工业实验室
    "deepmind": 10, "google deepmind": 10,
    "openai": 10,
    "anthropic": 9,
    "meta ai": 9, "facebook ai": 9, "fair": 9,
    "microsoft research": 8, "msr": 8,
    "nvidia": 8, "nvidia research": 8,
    "google research": 8, "google brain": 9,
    "apple": 7, "apple ml": 7,
    "amazon": 7, "amazon science": 7, "aws ai": 7,
    "huawei": 6, "huawei noah": 7,
    "alibaba": 6, "damo academy": 7,
    "tencent": 6, "tencent ai": 6,
    "bytedance": 6,
    
    # 顶级高校
    "stanford": 9, "stanford university": 9,
    "mit": 9, "massachusetts institute of technology": 9,
    "berkeley": 9, "uc berkeley": 9, "university of california, berkeley": 9,
    "cmu": 9, "carnegie mellon": 9,
    "princeton": 8, "princeton university": 8,
    "harvard": 8, "harvard university": 8,
    "tsinghua": 8, "tsinghua university": 8, "清华": 8,
    "pku": 8, "peking university": 8, "北京大学": 8,
    "eth": 8, "eth zurich": 8,
    "cambridge": 8, "university of cambridge": 8,
    "oxford": 8, "university of oxford": 8,
    "cornell": 7, "cornell university": 7,
    "columbia": 7, "columbia university": 7,
    "uw": 7, "university of washington": 7,
    "gatech": 7, "georgia tech": 7,
    "ucla": 7,
    "nyu": 7, "new york university": 7,
    "uiuc": 7, "university of illinois": 7,
}

# 顶级会议/期刊评分
TOP_VENUES = {
    # 顶级ML/AI会议
    "neurips": 10, "nips": 10,
    "icml": 10,
    "iclr": 10,
    "cvpr": 9,
    "iccv": 9,
    "eccv": 8,
    "acl": 9,
    "emnlp": 8,
    "naacl": 7,
    "aaai": 8,
    "ijcai": 7,
    "kdd": 8,
    "www": 7,
    "sigir": 7,
    "coling": 6,
    
    # 顶级期刊
    "nature": 10,
    "science": 10,
    "tpami": 9, "ieee transactions on pattern analysis": 9,
    "jmlr": 8, "journal of machine learning research": 8,
    "tacl": 8,
    "tmlr": 7, "transactions on machine learning research": 7,
    "ijcv": 7, "international journal of computer vision": 7,
}


class MultiDimensionScorer:
    """多维度评分器"""
    
    # 权重配置
    WEIGHT_SEMANTIC = 0.35
    WEIGHT_CITATION = 0.25
    WEIGHT_AUTHORITY = 0.25
    WEIGHT_VENUE = 0.15
    
    # 时间-引用过滤规则
    CITATION_AGE_RULES = [
        (14, 0),    # <14天，允许0引用
        (60, 1),    # 14-60天，至少1引用
        (180, 3),   # 60-180天，至少3引用
        (9999, 5),  # >180天，至少5引用
    ]
    
    def calculate_authority_score(
        self, 
        authors: List[str], 
        affiliations: List[str] = None
    ) -> float:
        """计算机构权威评分"""
        max_score = 0
        
        # 检查机构
        if affiliations:
            for affiliation in affiliations:
                aff_lower = affiliation.lower()
                for lab, score in TOP_LABS.items():
                    if lab in aff_lower:
                        max_score = max(max_score, score)
        
        # 从作者名中提取可能的机构信息（如 "Author Name (Google)"）
        for author in authors or []:
            author_lower = author.lower()
            for lab, score in TOP_LABS.items():
                if lab in author_lower:
                    max_score = max(max_score, score)
        
        return max_score
    
    def detect_venue(self, comments: str = None, categories: List[str] = None) -> Tuple[Optional[str], float]:
        """检测发表情况"""
        if not comments:
            return None, 0
        
        comments_lower = comments.lower()
        
        # 检测 "Accepted at X", "Published in X", "X 2024" 等模式
        patterns = [
            r"accepted (?:at|to|by) (\w+)",
            r"published (?:at|in) (\w+)",
            r"to appear (?:at|in) (\w+)",
            r"(\w+) (?:2023|2024|2025)",
        ]
        
        for venue_name, score in TOP_VENUES.items():
            if venue_name in comments_lower:
                return venue_name.upper(), score
        
        return None, 0
    
    def calculate_citation_score(
        self, 
        citation_count: int, 
        published_date: datetime
    ) -> float:
        """计算引用影响力分数（已有的二次衰减+速度公式）"""
        if not published_date:
            days = 180
        else:
            days = max(1, (datetime.utcnow() - published_date).days)
        
        # 二次时间衰减
        beta = 0.00001
        decay_factor = 1 + beta * (days ** 2)
        adjusted_citations = citation_count / decay_factor
        
        # 增长速度奖励
        citations_per_day = citation_count / max(days, 1)
        velocity_bonus = 1 + math.log(1 + citations_per_day * 100)
        
        velocity_score = adjusted_citations * velocity_bonus
        
        # 归一化到0-10（使用对数缩放）
        if velocity_score <= 0:
            return 0
        normalized = min(10, 2 * math.log(1 + velocity_score))
        return round(normalized, 2)
    
    def check_citation_threshold(
        self, 
        citation_count: int, 
        published_date: datetime
    ) -> bool:
        """检查论文是否满足时间-引用门槛"""
        if not published_date:
            return True  # 无日期信息，不过滤
        
        days = (datetime.utcnow() - published_date).days
        
        for max_days, min_citations in self.CITATION_AGE_RULES:
            if days <= max_days:
                return citation_count >= min_citations
        
        return True
    
    def calculate_final_score(
        self,
        semantic_score: float = 5.0,
        citation_count: int = 0,
        published_date: datetime = None,
        affiliations: List[str] = None,
        authors: List[str] = None,
        venue_comments: str = None,
    ) -> Dict:
        """计算多维度综合评分"""
        
        # 1. 语义相关度（直接使用传入值）
        semantic = semantic_score or 5.0
        
        # 2. 引用影响力
        citation = self.calculate_citation_score(citation_count, published_date)
        
        # 3. 机构权威
        authority = self.calculate_authority_score(authors, affiliations)
        
        # 4. 发表加成
        venue_name, venue_score = self.detect_venue(venue_comments)
        
        # 综合评分
        final = (
            self.WEIGHT_SEMANTIC * semantic +
            self.WEIGHT_CITATION * citation +
            self.WEIGHT_AUTHORITY * authority +
            self.WEIGHT_VENUE * venue_score
        )
        
        return {
            "semantic_score": round(semantic, 2),
            "citation_score": round(citation, 2),
            "authority_score": round(authority, 2),
            "venue_score": round(venue_score, 2),
            "venue_name": venue_name,
            "final_score": round(final, 2),
            "passes_threshold": self.check_citation_threshold(citation_count, published_date)
        }


# 全局实例
multi_scorer = MultiDimensionScorer()
