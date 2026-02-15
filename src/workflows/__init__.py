"""
Paper Agent - 工作流模块
"""
from .rating import RatingWorkflow
from .summarization import SummarizationWorkflow
from .extraction import ExtractionWorkflow
from .figure_analysis import FigureAnalysisWorkflow

__all__ = [
    "RatingWorkflow",
    "SummarizationWorkflow",
    "ExtractionWorkflow",
    "FigureAnalysisWorkflow"
]
