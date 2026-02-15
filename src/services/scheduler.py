"""
定时调度服务
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from ..config import rules_config

logger = structlog.get_logger(__name__)


def init_scheduler() -> AsyncIOScheduler:
    """初始化调度器"""
    scheduler = AsyncIOScheduler()
    
    # 从配置读取调度时间
    config = rules_config.load()
    scheduler_config = config.get("scheduler", {})
    fetch_time = scheduler_config.get("fetch_time", "08:00")
    timezone = scheduler_config.get("timezone", "Asia/Shanghai")
    
    # 解析时间
    hour, minute = map(int, fetch_time.split(":"))
    
    # 添加每日抓取任务
    scheduler.add_job(
        daily_fetch_job,
        CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="daily_fetch",
        name="Daily ArXiv Fetch",
        replace_existing=True
    )
    
    logger.info(
        "Scheduler initialized",
        fetch_time=fetch_time,
        timezone=timezone
    )
    
    return scheduler


async def daily_fetch_job():
    """每日抓取任务"""
    from .arxiv_fetcher import fetch_papers
    from .paper_processor import process_unprocessed_papers
    
    logger.info("Starting daily fetch job")
    
    try:
        # 抓取论文
        fetch_result = await fetch_papers()
        logger.info("Fetch completed", **fetch_result)
        
        # 处理未处理的论文
        process_result = await process_unprocessed_papers()
        logger.info("Processing completed", **process_result)
        
    except Exception as e:
        logger.error("Daily fetch job failed", error=str(e))
        raise
