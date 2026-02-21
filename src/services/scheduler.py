"""
定时调度 - 每日Track pipeline
"""
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from ..database import SessionLocal
from ..models import Digest, Paper, PaperRuleSet, RuleSet, Run
from . import app_settings
from .digest_generator import generate_monthly_report, generate_weekly_digest
from .email_service import send_digest, format_digest_html

logger = structlog.get_logger(__name__)


def _parse_cron(expr: str) -> dict[str, int]:
    """解析 cron 表达式 (minute hour day month day_of_week) 为 CronTrigger 参数"""
    parts = expr.strip().split()
    if len(parts) != 5:
        return {"hour": 8, "minute": 0}
    fields = {}
    if parts[0] != "*":
        fields["minute"] = int(parts[0])
    if parts[1] != "*":
        fields["hour"] = int(parts[1])
    if parts[2] != "*":
        fields["day"] = int(parts[2])
    if parts[3] != "*":
        fields["month"] = int(parts[3])
    if parts[4] != "*":
        fields["day_of_week"] = int(parts[4])
    return fields


def init_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    if not app_settings.get_bool("schedule_enabled"):
        logger.info("Scheduler disabled via settings")
        return scheduler

    track_cron = _parse_cron(app_settings.get("schedule_track_cron"))
    weekly_cron = _parse_cron(app_settings.get("schedule_weekly_cron"))
    monthly_cron = _parse_cron(app_settings.get("schedule_monthly_cron"))
    tz = app_settings.get("schedule_timezone") or "Asia/Shanghai"

    scheduler.add_job(
        daily_track_job,
        CronTrigger(**track_cron, timezone=tz),
        id="daily_track",
        name="Daily Track Pipeline",
        replace_existing=True,
    )

    scheduler.add_job(
        weekly_digest_job,
        CronTrigger(**weekly_cron, timezone=tz),
        id="weekly_digest",
        name="Weekly Digest Generation",
        replace_existing=True,
    )

    scheduler.add_job(
        monthly_report_job,
        CronTrigger(**monthly_cron, timezone=tz),
        id="monthly_report",
        name="Monthly Report Generation",
        replace_existing=True,
    )

    logger.info(
        "Scheduler initialized",
        track=app_settings.get("schedule_track_cron"),
        weekly=app_settings.get("schedule_weekly_cron"),
        monthly=app_settings.get("schedule_monthly_cron"),
        timezone=tz,
    )
    return scheduler


async def daily_track_job():
    from .pipeline import run_track

    logger.info("Starting daily track job")
    db = SessionLocal()
    try:
        active_rulesets = db.query(RuleSet).filter(
            RuleSet.is_active == True,
            RuleSet.is_initialized == True,
        ).all()

        for ruleset in active_rulesets:
            run = Run(
                ruleset_id=ruleset.id,
                run_type="track",
                status="pending",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = int(getattr(run, "id"))
            ruleset_id = int(getattr(ruleset, "id"))

            try:
                await run_track(run_id, ruleset_id)
            except Exception as e:
                logger.error("Track failed for ruleset", ruleset_id=ruleset.id, error=str(e))

    except Exception as e:
        logger.error("Daily track job failed", error=str(e))
    finally:
        db.close()


async def weekly_digest_job():
    logger.info("Starting weekly digest job")
    db = SessionLocal()
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=7)

    try:
        active_rulesets = db.query(RuleSet).filter(
            RuleSet.is_active == True,
            RuleSet.is_initialized == True,
        ).all()

        for ruleset in active_rulesets:
            try:
                rows = db.query(Paper, PaperRuleSet).join(
                    PaperRuleSet, Paper.id == PaperRuleSet.paper_id
                ).filter(
                    PaperRuleSet.ruleset_id == ruleset.id,
                    Paper.published_date >= period_start,
                ).order_by(Paper.published_date.desc().nullslast()).all()

                papers = [
                    {
                        "title": paper.title,
                        "score": assoc.llm_score,
                        "citations": paper.citation_count,
                        "year": paper.year,
                        "reason": assoc.llm_reason,
                    }
                    for paper, assoc in rows
                ]

                prev_digest = db.query(Digest).filter(
                    Digest.ruleset_id == ruleset.id,
                    Digest.digest_type == "weekly",
                ).order_by(Digest.created_at.desc()).first()
                prev_summary = str(prev_digest.content) if prev_digest else None
                topic_sentence = str(getattr(ruleset, "topic_sentence"))
                topic_name = str(getattr(ruleset, "name"))

                content = await generate_weekly_digest(
                    topic_sentence,
                    papers,
                    prev_summary=prev_summary,
                )
                if content is None:
                    logger.error("Weekly digest generation failed", ruleset_id=ruleset.id)
                    continue

                digest = Digest(
                    ruleset_id=ruleset.id,
                    digest_type="weekly",
                    content=content,
                    paper_count=len(papers),
                    period_start=period_start,
                    period_end=period_end,
                )
                db.add(digest)
                db.commit()
                db.refresh(digest)

                recipient = app_settings.get("digest_email_to")
                if recipient:
                    subject = f"[Paper Agent] {topic_name} Weekly Digest"
                    html_body = format_digest_html(content, "weekly", topic_name)
                    send_digest(recipient, subject, html_body,
                                digest_id=int(getattr(digest, "id")),
                                ruleset_id=int(getattr(ruleset, "id")),
                                topic_name=topic_name, digest_type="weekly")

                logger.info(
                    "Weekly digest generated",
                    ruleset_id=ruleset.id,
                    digest_id=digest.id,
                    paper_count=len(papers),
                )
            except Exception as e:
                db.rollback()
                logger.error("Weekly digest failed for ruleset", ruleset_id=ruleset.id, error=str(e))

    except Exception as e:
        logger.error("Weekly digest job failed", error=str(e))
    finally:
        db.close()


async def monthly_report_job():
    logger.info("Starting monthly report job")
    db = SessionLocal()
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=30)

    try:
        active_rulesets = db.query(RuleSet).filter(
            RuleSet.is_active == True,
            RuleSet.is_initialized == True,
        ).all()

        for ruleset in active_rulesets:
            try:
                rows = db.query(Paper, PaperRuleSet).join(
                    PaperRuleSet, Paper.id == PaperRuleSet.paper_id
                ).filter(
                    PaperRuleSet.ruleset_id == ruleset.id,
                    Paper.published_date >= period_start,
                ).order_by(Paper.published_date.desc().nullslast()).all()

                papers = [
                    {
                        "title": paper.title,
                        "score": assoc.llm_score,
                        "citations": paper.citation_count,
                        "year": paper.year,
                        "reason": assoc.llm_reason,
                    }
                    for paper, assoc in rows
                ]

                prev_digest = db.query(Digest).filter(
                    Digest.ruleset_id == ruleset.id,
                    Digest.digest_type == "monthly",
                ).order_by(Digest.created_at.desc()).first()
                prev_summary = str(prev_digest.content) if prev_digest else None
                topic_sentence = str(getattr(ruleset, "topic_sentence"))
                topic_name = str(getattr(ruleset, "name"))

                content = await generate_monthly_report(
                    topic_sentence,
                    papers,
                    prev_summary=prev_summary,
                )
                if content is None:
                    logger.error("Monthly report generation failed", ruleset_id=ruleset.id)
                    continue

                digest = Digest(
                    ruleset_id=ruleset.id,
                    digest_type="monthly",
                    content=content,
                    paper_count=len(papers),
                    period_start=period_start,
                    period_end=period_end,
                )
                db.add(digest)
                db.commit()
                db.refresh(digest)

                recipient = app_settings.get("digest_email_to")
                if recipient:
                    subject = f"[Paper Agent] {topic_name} 月报"
                    html_body = format_digest_html(content, "monthly", topic_name)
                    send_digest(recipient, subject, html_body,
                                digest_id=int(getattr(digest, "id")),
                                ruleset_id=int(getattr(ruleset, "id")),
                                topic_name=topic_name, digest_type="monthly")

                logger.info(
                    "Monthly report generated",
                    ruleset_id=ruleset.id,
                    digest_id=digest.id,
                    paper_count=len(papers),
                )
            except Exception as e:
                db.rollback()
                logger.error("Monthly report failed for ruleset", ruleset_id=ruleset.id, error=str(e))

    except Exception as e:
        logger.error("Monthly report job failed", error=str(e))
    finally:
        db.close()
