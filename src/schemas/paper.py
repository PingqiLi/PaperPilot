"""
Pydantic模型定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ Paper Schemas ============

class PaperBase(BaseModel):
    """论文基础模型"""
    arxiv_id: str
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    categories: List[str] = []
    published_date: Optional[datetime] = None
    pdf_url: Optional[str] = None


class PaperCreate(PaperBase):
    """创建论文"""
    pass


class PaperSummary(BaseModel):
    """论文摘要（列表展示用）"""
    id: int
    arxiv_id: str
    title: str
    authors: List[str]
    categories: List[str]
    published_date: Optional[datetime]
    relevance_score: Optional[float]
    is_starred: bool = False
    is_read: bool = False
    
    class Config:
        from_attributes = True


class PaperDetail(PaperBase):
    """论文详情"""
    id: int
    is_processed: bool
    markdown_content: Optional[str]
    relevance_score: Optional[float]
    score_reason: Optional[str]
    summary: Optional[str]
    key_findings: Optional[List[str]]
    methodology: Optional[str]
    extracted_info: Optional[Dict[str, Any]]
    analysis: Optional[List[Dict[str, Any]]] = None
    figures: Optional[List[Dict[str, Any]]] = None
    is_starred: bool
    is_read: bool
    user_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaperUpdate(BaseModel):
    """更新论文"""
    is_starred: Optional[bool] = None
    is_read: Optional[bool] = None
    user_notes: Optional[str] = None
    feedback: Optional[str] = None  # "valuable", "not_valuable", None


# ============ Workflow Output Schemas ============

class RatingResult(BaseModel):
    """评分工作流输出"""
    score: int = Field(ge=1, le=10)
    reason: str


class SummaryResult(BaseModel):
    """摘要工作流输出"""
    core_contribution: str
    methodology: str
    main_results: str
    limitations: Optional[str] = None


class ExtractionResult(BaseModel):
    """抽取工作流输出"""
    title: str
    authors: List[str]
    keywords: List[str]
    datasets: List[str] = []
    baselines: List[str] = []
    metrics: Dict[str, Any] = {}


# ============ API Response Schemas ============

class PaperListResponse(BaseModel):
    """论文列表响应"""
    total: int
    page: int
    page_size: int
    items: List[PaperSummary]


class FetchStatus(BaseModel):
    """抓取状态"""
    last_fetch: Optional[datetime]
    next_fetch: Optional[datetime]
    total_papers: int
    papers_today: int


# ============ Rules Schemas ============

class KeywordsConfig(BaseModel):
    include: List[str] = []
    exclude: List[str] = []


class AdvancedRulesConfig(BaseModel):
    authors: List[str] = []
    score_threshold: int = 5
    max_papers_per_fetch: int = 100


class CostConfig(BaseModel):
    daily_token_limit: int = 0
    prefer_local_llm: bool = True


class RulesConfig(BaseModel):
    """规则配置"""
    categories: List[str] = []
    keywords: KeywordsConfig = KeywordsConfig()
    date_range: int = 7
    interests: str = ""
    advanced: AdvancedRulesConfig = AdvancedRulesConfig()
    cost: CostConfig = CostConfig()
    s2_api_key: Optional[str] = None


class RulesUpdateRequest(BaseModel):
    """更新规则请求"""
    rules: RulesConfig
