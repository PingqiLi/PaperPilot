"""
规则集数据模型
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, 
    DateTime, ForeignKey, JSON, Table
)
from sqlalchemy.orm import relationship

from .paper import Base


class RuleSet(Base):
    """规则集表 - 支持多个独立的论文筛选规则"""
    __tablename__ = "rulesets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)  # 如 "推理优化"
    description = Column(Text)  # 自然语言描述
    topic_description = Column(Text)  # 用于Agent筛选的详细Topic描述
    
    # 筛选规则
    categories = Column(JSON, default=list)  # ["cs.AI", "cs.LG"]
    keywords_include = Column(JSON, default=list)  # 包含关键词
    keywords_exclude = Column(JSON, default=list)  # 排除关键词
    semantic_query = Column(Text)  # 语义搜索主题描述
    expanded_keywords = Column(JSON, default=list)  # LLM扩展的关键词
    
    # 时间范围
    date_range_days = Column(Integer, default=30)  # 默认30天
    
    # Collect（历史精选）配置
    collect_count = Column(Integer, default=50)  # 精选数量
    collect_range_days = Column(Integer, default=1095)  # 精选时间范围（默认3年）
    is_collected = Column(Boolean, default=False)  # 是否已完成初始收集
    collected_at = Column(DateTime)  # 收集完成时间
    
    # Track（追踪新论文）配置
    track_range_days = Column(Integer, default=7)  # 追踪时间范围（默认7天）
    last_track_at = Column(DateTime)  # 上次追踪时间
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # 是否为默认规则集
    
    # 抓取统计
    last_fetch_at = Column(DateTime)
    total_papers = Column(Integer, default=0)
    curated_count = Column(Integer, default=0)  # 精选论文数
    new_count = Column(Integer, default=0)  # 新论文数
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    paper_associations = relationship("PaperRuleSet", back_populates="ruleset")
    
    def __repr__(self):
        return f"<RuleSet(id={self.id}, name='{self.name}')>"


class PaperRuleSet(Base):
    """论文-规则集关联表"""
    __tablename__ = "paper_rulesets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"), nullable=False)
    
    # 语义评分
    semantic_score = Column(Float)  # LLM评分 0-10
    score_reason = Column(Text)  # 评分理由
    
    # 论文分类
    is_curated = Column(Boolean, default=False)  # 是否为精选论文（Collect阶段）
    is_new = Column(Boolean, default=True)  # 是否为新论文（Track阶段）
    
    # 状态
    is_scored = Column(Boolean, default=False)  # 是否已完成LLM评分
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    scored_at = Column(DateTime)
    
    # 关联
    paper = relationship("Paper", back_populates="ruleset_associations")
    ruleset = relationship("RuleSet", back_populates="paper_associations")
    
    def __repr__(self):
        return f"<PaperRuleSet(paper_id={self.paper_id}, ruleset_id={self.ruleset_id}, score={self.semantic_score})>"
