"""
Pydantic schemas - v1.0.0 API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


# --- RuleSet ---

class RuleSetDraftRequest(BaseModel):
    topic_sentence: str = Field(..., min_length=5, max_length=500)


class RuleSetDraftResponse(BaseModel):
    name: str
    topic_sentence: str
    categories: List[str] = []
    keywords_include: List[str] = []
    keywords_exclude: List[str] = []
    search_queries: List[str] = []
    method_queries: List[str] = []


class RuleSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    topic_sentence: str = Field(..., min_length=5)
    categories: List[str] = []
    keywords_include: List[str] = []
    keywords_exclude: List[str] = []
    search_queries: List[str] = []
    method_queries: List[str] = []
    source_filter: str = Field(default="all", pattern="^(all|arxiv|open_access)$")


class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    topic_sentence: Optional[str] = None
    categories: Optional[List[str]] = None
    keywords_include: Optional[List[str]] = None
    keywords_exclude: Optional[List[str]] = None
    search_queries: Optional[List[str]] = None
    method_queries: Optional[List[str]] = None
    source_filter: Optional[str] = Field(default=None, pattern="^(all|arxiv|open_access)$")
    is_active: Optional[bool] = None


class RuleSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    topic_sentence: str
    categories: List[str]
    keywords_include: List[str]
    keywords_exclude: List[str]
    search_queries: List[str]
    method_queries: List[str] = []
    source_filter: str = "all"
    is_active: bool
    is_initialized: bool
    last_track_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# --- Run ---

class RunCreate(BaseModel):
    run_type: str = Field(..., pattern="^(initialize|track)$")
    # 重新初始化：清除非收藏论文后再执行 initialize
    reinit: bool = False


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ruleset_id: int
    run_type: str
    status: str
    progress: Dict[str, Any] = {}
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


# --- Paper ---

class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    arxiv_id: str
    s2_id: Optional[str]
    title: str
    authors: List[str]
    abstract: Optional[str]
    categories: List[str]
    published_date: Optional[datetime]
    year: Optional[int]
    venue: Optional[str]
    pdf_url: Optional[str]
    citation_count: int
    influential_citation_count: int
    impact_score: float
    is_survey: bool = False


class PaperWithScore(BaseModel):
    id: int
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: Optional[str]
    categories: List[str]
    published_date: Optional[datetime]
    year: Optional[int]
    venue: Optional[str]
    pdf_url: Optional[str]
    citation_count: int
    influential_citation_count: int = 0
    impact_score: float
    is_survey: bool = False
    llm_score: Optional[float]
    llm_reason: Optional[str]
    status: str
    source: str
    topic_id: Optional[int] = None
    analysis: Optional[Dict[str, Any]] = None
    analyzed_at: Optional[datetime] = None
    is_new: bool = False


class PaperStatusUpdate(BaseModel):
    # "inbox" | "archived" | "favorited"
    status: str = Field(..., pattern="^(inbox|archived|favorited)$")


class PaperListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PaperWithScore]


# --- Overview ---

class PaperPreview(BaseModel):
    id: int
    arxiv_id: str
    title: str
    llm_score: Optional[float]
    llm_reason: Optional[str]
    is_survey: bool = False
    year: Optional[int]
    venue: Optional[str]


class TopicPaperCounts(BaseModel):
    total: int = 0
    initialize: int = 0
    track: int = 0
    favorited: int = 0


class TopicOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    topic_sentence: str
    is_initialized: bool
    created_at: datetime
    last_track_at: Optional[datetime] = None
    track_latest_count: int = 0
    paper_counts: TopicPaperCounts
    top_papers: List[PaperPreview]
