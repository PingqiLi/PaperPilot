"""
数据模型 - v1.0.0
精简模型：只存元数据，不存论文全文
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    arxiv_id = Column(String(50), unique=True, index=True, nullable=False)
    s2_id = Column(String(100), index=True)
    title = Column(String(500), nullable=False)
    authors = Column(JSON, default=list)
    abstract = Column(Text)
    categories = Column(JSON, default=list)
    published_date = Column(DateTime)
    year = Column(Integer)
    venue = Column(String(200))
    pdf_url = Column(String(500))

    citation_count = Column(Integer, default=0)
    influential_citation_count = Column(Integer, default=0)
    impact_score = Column(Float, default=0.0)
    is_survey = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ruleset_associations = relationship("PaperRuleSet", back_populates="paper")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    model = Column(String(100))
    workflow = Column(String(50))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_yuan = Column(Float, default=0.0)
