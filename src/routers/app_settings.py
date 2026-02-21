from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import structlog

from ..database import get_db
from ..models.email_log import EmailLog
from ..services import app_settings
from ..services.batch_scorer import DEFAULT_SCORING_RUBRIC
from ..services.email_service import send_digest
from ..services.llm_client import load_prompt, get_default_custom_section

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("")
def get_settings():
    return app_settings.get_all()


@router.put("")
def update_settings(data: dict[str, Any]):
    valid_keys = [k for k in data if k in app_settings.SETTINGS_SCHEMA]
    if not valid_keys:
        return {"updated": 0}

    app_settings.set_many({k: data[k] for k in valid_keys})
    logger.info("Settings updated", keys=valid_keys)
    return {"updated": len(valid_keys), "keys": valid_keys}


@router.get("/prompts/defaults")
def get_prompt_defaults():
    return {
        "batch_scoring_rubric": DEFAULT_SCORING_RUBRIC,
        "field_overview": get_default_custom_section("field_overview"),
        "weekly_digest": get_default_custom_section("weekly_digest"),
        "monthly_report": get_default_custom_section("monthly_report"),
        "paper_analysis": get_default_custom_section("paper_analysis"),
    }


@router.get("/emails")
def list_email_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(EmailLog).order_by(EmailLog.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": log.id,
            "recipient": log.recipient,
            "subject": log.subject,
            "status": log.status,
            "error": log.error,
            "topic_name": log.topic_name,
            "digest_type": log.digest_type,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in rows
    ]
    return {"total": total, "items": items}


@router.post("/emails/test")
def send_test_email():
    recipient = app_settings.get("digest_email_to")
    if not recipient:
        return {"status": "error", "message": "未配置收件人地址 (Recipient)"}

    host = app_settings.get("smtp_host")
    if not host:
        return {"status": "error", "message": "未配置 SMTP Host"}

    subject = "[PaperPilot] Test Email"
    html_body = (
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>"
        "<div style='max-width:600px;margin:40px auto;padding:32px;border:1px solid #e5e7eb;border-radius:12px;'>"
        "<h2 style='margin:0 0 8px;color:#111827;'>PaperPilot</h2>"
        "<p style='color:#6b7280;margin:0 0 16px;'>Email configuration is working correctly.</p>"
        "<p style='color:#6b7280;margin:0;font-size:13px;'>This is a test email sent from your PaperPilot instance.</p>"
        "</div></body></html>"
    )
    try:
        send_digest(recipient, subject, html_body, digest_type="test")
    except Exception as e:
        return {"status": "error", "message": f"发送失败: {e}"}
    return {"status": "ok", "message": f"Test email sent to {recipient}"}
