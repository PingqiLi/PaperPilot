"""
Paper Agent - ArXiv论文筛选与摘要系统
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .config import settings
from .routers import papers, rules, health, rulesets
from .services.scheduler import init_scheduler

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting Paper Agent...")
    
    # 初始化调度器
    scheduler = init_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    
    yield
    
    # 清理
    scheduler.shutdown()
    logger.info("Paper Agent stopped")


app = FastAPI(
    title="Paper Agent",
    description="ArXiv论文筛选与摘要系统",
    version="0.1.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["Health"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["Papers"])
app.include_router(rules.router, prefix="/api/v1/rules", tags=["Rules"])
app.include_router(rulesets.router, tags=["RuleSets"])


@app.get("/")
async def root():
    return {
        "name": "Paper Agent",
        "version": "0.1.0",
        "docs": "/docs"
    }
