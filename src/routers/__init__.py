"""
Paper Agent - 路由模块
"""
from .health import router as health_router
from .papers import router as papers_router
from .rules import router as rules_router
from .rulesets import router as rulesets_router
from . import health, papers, rules, rulesets

__all__ = ["health_router", "papers_router", "rules_router", "rulesets_router",
           "health", "papers", "rules", "rulesets"]
