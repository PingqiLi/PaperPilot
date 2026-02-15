"""
Paper Agent - Pydantic模型
"""
from .paper import (
    PaperBase,
    PaperCreate,
    PaperSummary,
    PaperDetail,
    PaperUpdate,
    PaperListResponse,
    FetchStatus,
    RatingResult,
    SummaryResult,
    ExtractionResult,
    RulesConfig,
    RulesUpdateRequest
)

__all__ = [
    "PaperBase",
    "PaperCreate",
    "PaperSummary",
    "PaperDetail",
    "PaperUpdate",
    "PaperListResponse",
    "FetchStatus",
    "RatingResult",
    "SummaryResult",
    "ExtractionResult",
    "RulesConfig",
    "RulesUpdateRequest"
]
