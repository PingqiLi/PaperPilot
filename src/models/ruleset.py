"""
规则集、运行记录、论文关联模型
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from .paper import Base


class RuleSet(Base):
    __tablename__ = "rulesets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    topic_sentence = Column(Text, nullable=False)

    categories = Column(JSON, default=list)
    keywords_include = Column(JSON, default=list)
    keywords_exclude = Column(JSON, default=list)
    search_queries = Column(JSON, default=list)
    method_queries = Column(JSON, default=list)
    source_filter = Column(String(20), default="all")  # "all" | "arxiv" | "open_access"
    init_sources = Column(String(50))
    track_sources = Column(String(50))

    is_active = Column(Boolean, default=True)
    is_initialized = Column(Boolean, default=False)
    last_track_at = Column("last_monitor_at", DateTime)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper_associations = relationship("PaperRuleSet", back_populates="ruleset")
    runs = relationship("Run", back_populates="ruleset")

    def __repr__(self):
        return f"<RuleSet(id={self.id}, name='{self.name}')>"


class Run(Base):
    """异步运行记录 (Initialize / Track)"""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"), nullable=False)
    run_type = Column(String(20), nullable=False)  # "initialize" | "track"
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    progress = Column(JSON, default=dict)  # {"stage": "...", "done": N, "total": M}
    error = Column(Text)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    ruleset = relationship("RuleSet", back_populates="runs")

    def __repr__(self):
        return f"<Run(id={self.id}, type={self.run_type}, status={self.status})>"


class PaperRuleSet(Base):
    __tablename__ = "paper_rulesets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"), nullable=False)

    # "inbox" | "archived" | "favorited"
    status = Column(String(20), default="inbox")
    # "initialize" | "track"
    source = Column(String(20), default="initialize")

    llm_score = Column(Float)
    llm_reason = Column(Text)
    is_scored = Column(Boolean, default=False)
    analysis = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    scored_at = Column(DateTime)
    analyzed_at = Column(DateTime)

    paper = relationship("Paper", back_populates="ruleset_associations")
    ruleset = relationship("RuleSet", back_populates="paper_associations")

    def __repr__(self):
        return f"<PaperRuleSet(paper={self.paper_id}, ruleset={self.ruleset_id}, score={self.llm_score})>"
