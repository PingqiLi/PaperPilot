"""
数据模型定义
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Paper(Base):
    """论文模型"""
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    arxiv_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    authors = Column(JSON, default=list)  # List[str]
    abstract = Column(Text)
    categories = Column(JSON, default=list)  # List[str]
    published_date = Column(DateTime)
    updated_date = Column(DateTime)
    pdf_url = Column(String(500))
    
    # 处理状态
    is_processed = Column(Boolean, default=False)
    markdown_content = Column(Text)  # PDF解析后的Markdown
    
    # LLM处理结果
    relevance_score = Column(Float)  # 相关性评分 1-10
    score_reason = Column(Text)  # 评分理由
    summary = Column(Text)  # 论文摘要
    key_findings = Column(JSON)  # 关键发现 List[str]
    methodology = Column(Text)  # 方法论
    extracted_info = Column(JSON)  # 抽取的结构化信息
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 用户交互
    is_starred = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    user_notes = Column(Text)
    
    # 引用数（从Semantic Scholar获取）
    citation_count = Column(Integer, default=0)
    citation_updated_at = Column(DateTime)
    semantic_scholar_id = Column(String(100))  # Semantic Scholar论文ID
    
    # 多维度评分（新增）
    affiliations = Column(JSON, default=list)  # 作者机构列表
    venue = Column(String(200))  # 发表会议/期刊名称
    venue_score = Column(Float, default=0)  # 发表加成分 0-10
    authority_score = Column(Float, default=0)  # 机构权威分 0-10
    final_score = Column(Float)  # 综合最终得分

    # 图表分析结果
    analysis = Column(JSON)  # 图表分析结果 List[Dict]
    figures = Column(JSON)  # 图表元数据 List[Dict]
    
    # 用户反馈
    feedback = Column(String(20))  # "valuable", "not_valuable", None
    feedback_at = Column(DateTime)
    
    # 规则集关联
    ruleset_associations = relationship("PaperRuleSet", back_populates="paper")


class FetchLog(Base):
    """抓取日志"""
    __tablename__ = "fetch_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    fetch_time = Column(DateTime, default=datetime.utcnow)
    categories = Column(JSON)  # 抓取的分类
    total_fetched = Column(Integer, default=0)
    total_filtered = Column(Integer, default=0)  # 通过筛选的数量
    total_processed = Column(Integer, default=0)  # LLM处理的数量
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    error_message = Column(Text)
    duration_seconds = Column(Float)


class TokenUsage(Base):
    """Token使用记录"""
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    backend = Column(String(50))  # openai, ollama, vllm
    model = Column(String(100))
    workflow = Column(String(50))  # rating, summarization, extraction
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)  # 估算成本
