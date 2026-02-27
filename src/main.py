"""
Paper Agent v1.0.0
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from sqlalchemy import text

from .config import settings
from .database import SessionLocal, init_db
from .routers import app_settings, digests, health, papers, rules, rulesets, stats, tasks
from .services.scheduler import init_scheduler, startup_catchup

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
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Paper Agent v1.0.0")

    init_db()
    _migrate_monitor_to_track()
    logger.info("Database initialized")

    _cleanup_orphaned_runs()

    scheduler = init_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    asyncio.get_event_loop().create_task(startup_catchup())

    yield

    scheduler.shutdown()
    logger.info("Paper Agent stopped")


def _migrate_monitor_to_track():
    db = SessionLocal()
    try:
        db.execute(text("UPDATE runs SET run_type='track' WHERE run_type='monitor'"))
        db.execute(text("UPDATE paper_rulesets SET source='track' WHERE source='monitor'"))
        db.execute(text("UPDATE paper_rulesets SET source='initialize' WHERE source IN ('citation','method')"))
        db.execute(text("UPDATE app_settings SET key='schedule_track_cron' WHERE key='schedule_monitor_cron'"))
        db.execute(text("UPDATE app_settings SET key='track_top_n' WHERE key='monitor_top_n'"))
        db.commit()
        logger.info("Migration monitor->track completed")
    except Exception as e:
        db.rollback()
        logger.warning("Migration monitor->track skipped", error=str(e))

    try:
        db.execute(text("ALTER TABLE rulesets ADD COLUMN display_order INTEGER DEFAULT 0"))
        db.commit()
        logger.info("Migration display_order column added")
    except Exception as e:
        db.rollback()

    db.close()



def _cleanup_orphaned_runs():
    db = SessionLocal()
    try:
        from .models import Run
        from .models.task import Task
        from datetime import datetime
        stuck_runs = db.query(Run).filter(Run.status.in_(["pending", "running"])).all()
        for run in stuck_runs:
            run.status = "failed"
            run.error = "Interrupted by server restart"
            if not run.completed_at:
                run.completed_at = datetime.utcnow()
            stuck_tasks = db.query(Task).filter(
                Task.run_id == run.id,
                Task.status.in_(["pending", "running"]),
            ).all()
            for task in stuck_tasks:
                task.status = "failed"
                task.error = "Interrupted by server restart"
                if not task.completed_at:
                    task.completed_at = datetime.utcnow()
        if stuck_runs:
            db.commit()
            logger.info("Cleaned up orphaned runs", count=len(stuck_runs),
                        run_ids=[r.id for r in stuck_runs])
        else:
            logger.info("No orphaned runs found")
    except Exception as e:
        db.rollback()
        logger.warning("Orphaned run cleanup failed", error=str(e))
    finally:
        db.close()

app = FastAPI(
    title="Paper Agent",
    description="ArXiv论文智能筛选系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["Papers"])
app.include_router(rules.router, prefix="/api/v1/rules", tags=["Rules"])
app.include_router(rulesets.router, tags=["RuleSets"])
app.include_router(digests.router, prefix="/api/v1/rulesets", tags=["digests"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Stats"])
app.include_router(tasks.router)
app.include_router(app_settings.router, tags=["Settings"])


@app.get("/")
async def root():
    return {"name": "Paper Agent", "version": "1.0.0", "docs": "/docs"}
