import html
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import structlog

from ..database import SessionLocal
from ..models.email_log import EmailLog
from . import app_settings

logger = structlog.get_logger(__name__)


_TYPE_LABELS = {"field_overview": "领域概览", "weekly": "周报", "monthly": "月报"}

_MATURITY_STYLES = {
    "emerging": "background:#fef3c7;color:#d97706;",
    "active": "background:#d1fae5;color:#059669;",
    "mature": "background:#e0e7ff;color:#4f46e5;",
}

_READING_STAGES = [
    ("start_with", "start_reason", "📖 入门必读"),
    ("then_read", "then_reason", "🔬 进阶理解"),
    ("deep_dive", "deep_reason", "🚀 深入研究"),
]

_MOMENTUM_LABELS = [
    ("accelerating", "🔥 加速发展"),
    ("emerging", "🌱 新兴方向"),
    ("declining", "📉 趋于平缓"),
]

_S = {
    "body": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f9fafb;margin:0;padding:0;",
    "wrap": "max-width:680px;margin:0 auto;padding:32px 16px;",
    "header": "padding:24px;border-radius:12px 12px 0 0;background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;",
    "card": "background:#fff;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:16px;overflow:hidden;",
    "section": "padding:20px 24px;",
    "h2": "margin:0 0 4px 0;font-size:20px;font-weight:700;color:#fff;",
    "subtitle": "margin:0;font-size:13px;color:rgba(255,255,255,0.7);",
    "h3": "margin:0 0 12px 0;font-size:15px;font-weight:600;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:8px;",
    "text": "margin:0 0 8px 0;font-size:14px;line-height:1.7;color:#374151;",
    "muted": "font-size:12px;color:#6b7280;line-height:1.6;",
    "pillar": "padding:14px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;background:#fafafa;",
    "badge": "display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:500;",
    "chip": "display:inline-block;font-size:12px;padding:3px 10px;border-radius:6px;background:#f3f4f6;border:1px solid #e5e7eb;color:#4f46e5;text-decoration:none;margin:2px;",
    "stage": "padding:14px;border-radius:8px;margin-bottom:8px;background:#f9fafb;border-left:3px solid #6366f1;",
    "li": "margin-bottom:8px;font-size:14px;line-height:1.6;color:#374151;",
    "link": "color:#4f46e5;text-decoration:none;font-weight:500;",
    "cluster": "padding:14px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;background:#fafafa;",
    "footer": "text-align:center;padding:16px;font-size:11px;color:#9ca3af;",
}


def _esc(text: Any) -> str:
    return html.escape(str(text)) if text else ""


def _paper_url(arxiv_id: str) -> str:
    if not arxiv_id:
        return ""
    if arxiv_id.startswith("s2:"):
        return f"https://www.semanticscholar.org/paper/{arxiv_id[3:]}"
    return f"https://arxiv.org/abs/{arxiv_id}"


def _resolve(refs: list[dict[str, Any]], index: int) -> Optional[dict[str, Any]]:
    for r in refs:
        if r.get("index") == index:
            return r
    return None


def _paper_link(refs: list[dict[str, Any]], index: int) -> str:
    ref = _resolve(refs, index)
    if not ref:
        return f"<span style='{_S['muted']}'>Paper #{index}</span>"
    url = _paper_url(ref.get("arxiv_id", ""))
    title = _esc(ref.get("title", f"Paper #{index}"))
    if url:
        return f"<a href='{url}' style='{_S['link']}' target='_blank'>{title}</a>"
    return f"<span style='font-weight:500;color:#111827;'>{title}</span>"


def _paper_chip(refs: list[dict[str, Any]], index: int) -> str:
    ref = _resolve(refs, index)
    if not ref:
        return f"<span style='{_S['chip']}'>Paper #{index}</span>"
    title = _esc(ref.get("title", ""))
    if len(title) > 45:
        title = title[:45] + "…"
    url = _paper_url(ref.get("arxiv_id", ""))
    if url:
        return f"<a href='{url}' style='{_S['chip']}' target='_blank'>{title}</a>"
    return f"<span style='{_S['chip']}'>{title}</span>"


def _section(title: str, body: str) -> str:
    return (
        f"<div style='{_S['section']}'>"
        f"<h3 style='{_S['h3']}'>{_esc(title)}</h3>"
        f"{body}"
        "</div>"
    )


def _fmt_field_overview(c: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    parts = []

    if c.get("summary"):
        parts.append(_section("概要", f"<p style='{_S['text']}'>{_esc(c['summary'])}</p>"))

    if c.get("pillars"):
        pillars_html = ""
        for p in c["pillars"]:
            badge = ""
            if p.get("maturity"):
                ms = _MATURITY_STYLES.get(p["maturity"], "background:#f3f4f6;color:#6b7280;")
                badge = f" <span style='{_S['badge']}{ms}'>{_esc(p['maturity'])}</span>"
            chips = ""
            if p.get("key_papers"):
                chips = (
                    "<div style='margin-top:8px;'>"
                    + "".join(_paper_chip(refs, idx) for idx in p["key_papers"])
                    + "</div>"
                )
            pillars_html += (
                f"<div style='{_S['pillar']}'>"
                f"<div style='margin-bottom:6px;font-size:14px;font-weight:600;color:#111827;'>{_esc(p.get('name'))}{badge}</div>"
                f"<p style='{_S['muted']}margin:0;'>{_esc(p.get('description'))}</p>"
                f"{chips}"
                "</div>"
            )
        parts.append(_section("研究支柱", pillars_html))

    rp = c.get("reading_path")
    if rp:
        stages_html = ""
        for key, reason_key, label in _READING_STAGES:
            indices = rp.get(key)
            if not indices:
                continue
            if not isinstance(indices, list):
                indices = [indices]
            reason = rp.get(reason_key, "")
            paper_links = "<br>".join(
                f"• {_paper_link(refs, idx)}" for idx in indices
            )
            reason_html = f"<p style='{_S['muted']}margin-top:6px;margin-bottom:0;'>{_esc(reason)}</p>" if reason else ""
            stages_html += (
                f"<div style='{_S['stage']}'>"
                f"<div style='font-size:13px;font-weight:600;color:#312e81;margin-bottom:6px;'>{label}</div>"
                f"<div style='font-size:14px;line-height:1.8;color:#374151;'>{paper_links}</div>"
                f"{reason_html}"
                "</div>"
            )
        if stages_html:
            parts.append(_section("阅读路径", stages_html))

    if c.get("open_problems"):
        items = "".join(
            f"<li style='{_S['li']}'>{_esc(p)}</li>" for p in c["open_problems"]
        )
        parts.append(_section("开放问题", f"<ol style='margin:0;padding-left:20px;'>{items}</ol>"))

    return "".join(parts)


def _fmt_weekly(c: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    parts = []

    if c.get("week_summary"):
        parts.append(_section("本周概要", f"<p style='{_S['text']}'>{_esc(c['week_summary'])}</p>"))

    if c.get("must_read"):
        items = ""
        for item in c["must_read"]:
            link = _paper_link(refs, item.get("index", 0))
            why = _esc(item.get("why", ""))
            items += f"<li style='{_S['li']}'>{link}{' — ' + why if why else ''}</li>"
        parts.append(_section("必读论文", f"<ul style='margin:0;padding-left:20px;'>{items}</ul>"))

    if c.get("worth_noting"):
        items = ""
        for item in c["worth_noting"]:
            link = _paper_link(refs, item.get("index", 0))
            note = _esc(item.get("one_liner", ""))
            items += f"<li style='{_S['li']}'>{link}{' — ' + note if note else ''}</li>"
        parts.append(_section("值得关注", f"<ul style='margin:0;padding-left:20px;'>{items}</ul>"))

    if c.get("trend_signal"):
        parts.append(_section("趋势信号", f"<p style='{_S['text']}'>{_esc(c['trend_signal'])}</p>"))

    if c.get("skip_reason"):
        parts.append(_section("可跳过", f"<p style='{_S['muted']}'>{_esc(c['skip_reason'])}</p>"))

    return "".join(parts)


def _fmt_monthly(c: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    parts = []

    if c.get("month_summary"):
        parts.append(_section("月度概要", f"<p style='{_S['text']}'>{_esc(c['month_summary'])}</p>"))

    if c.get("highlights"):
        items = ""
        for item in c["highlights"]:
            link = _paper_link(refs, item.get("index", 0))
            sig = _esc(item.get("significance", ""))
            items += f"<li style='{_S['li']}'>{link}{' — ' + sig if sig else ''}</li>"
        parts.append(_section("本月亮点", f"<ul style='margin:0;padding-left:20px;'>{items}</ul>"))

    if c.get("clusters"):
        clusters_html = ""
        for cl in c["clusters"]:
            theme = _esc(cl.get("theme") or cl.get("name", ""))
            insight = cl.get("insight", "")
            indices = cl.get("paper_indices") or cl.get("papers") or []
            chips = "".join(_paper_chip(refs, idx) for idx in indices) if indices else ""
            clusters_html += (
                f"<div style='{_S['cluster']}'>"
                f"<div style='font-size:14px;font-weight:600;color:#111827;margin-bottom:4px;'>{theme}"
                f" <span style='{_S['muted']}'>{len(indices)} papers</span></div>"
                + (f"<p style='{_S['text']}'>{_esc(insight)}</p>" if insight else "")
                + (f"<div style='margin-top:4px;'>{chips}</div>" if chips else "")
                + "</div>"
            )
        parts.append(_section("论文聚类", clusters_html))

    momentum = c.get("momentum")
    if momentum and isinstance(momentum, dict):
        mom_html = ""
        for key, label in _MOMENTUM_LABELS:
            items = momentum.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            list_html = "".join(f"<li style='{_S['li']}'>{_esc(item)}</li>" for item in items)
            mom_html += (
                f"<div style='margin-bottom:10px;'>"
                f"<div style='font-size:13px;font-weight:600;color:#374151;margin-bottom:4px;'>{label}</div>"
                f"<ul style='margin:0;padding-left:20px;'>{list_html}</ul>"
                "</div>"
            )
        if mom_html:
            parts.append(_section("研究动向", mom_html))

    if c.get("next_month_watch"):
        text = c["next_month_watch"]
        if isinstance(text, list):
            text = "；".join(str(t) for t in text)
        parts.append(_section("下月关注", f"<p style='{_S['text']}'>{_esc(text)}</p>"))

    return "".join(parts)


def format_digest_html(digest_content: dict[str, Any], digest_type: str, topic_name: str) -> str:
    if not isinstance(digest_content, dict):
        digest_content = {"raw": str(digest_content)}

    refs = digest_content.get("paper_references") or []
    label = _TYPE_LABELS.get(digest_type, digest_type)

    formatters = {
        "field_overview": _fmt_field_overview,
        "weekly": _fmt_weekly,
        "monthly": _fmt_monthly,
    }
    fmt = formatters.get(digest_type)
    if fmt:
        body = fmt(digest_content, refs)
    else:
        fallback = html.escape(json.dumps(digest_content, ensure_ascii=False, indent=2))
        body = f"<div style='{_S['section']}'><pre style='white-space:pre-wrap;font-size:13px;'>{fallback}</pre></div>"

    return (
        f"<html><head><meta charset='utf-8'></head><body style='{_S['body']}'>"
        f"<div style='{_S['wrap']}'>"
        f"<div style='{_S['card']}'>"
        f"<div style='{_S['header']}'>"
        f"<h2 style='{_S['h2']}'>{_esc(topic_name)}</h2>"
        f"<p style='{_S['subtitle']}'>{label}</p>"
        "</div>"
        f"{body}"
        "</div>"
        f"<div style='{_S['footer']}'>Sent by PaperPilot</div>"
        "</div>"
        "</body></html>"
    )


def _log_email(
    recipient: str,
    subject: str,
    status: str,
    error: Optional[str] = None,
    digest_id: Optional[int] = None,
    ruleset_id: Optional[int] = None,
    topic_name: Optional[str] = None,
    digest_type: Optional[str] = None,
):
    db = SessionLocal()
    try:
        log = EmailLog(
            recipient=recipient,
            subject=subject,
            status=status,
            error=error,
            digest_id=digest_id,
            ruleset_id=ruleset_id,
            topic_name=topic_name,
            digest_type=digest_type,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning("Failed to log email", error=str(e))
    finally:
        db.close()


def send_digest(
    to_addr: str,
    subject: str,
    html_body: str,
    digest_id: Optional[int] = None,
    ruleset_id: Optional[int] = None,
    topic_name: Optional[str] = None,
    digest_type: Optional[str] = None,
):
    host = app_settings.get("smtp_host")
    port = app_settings.get_int("smtp_port")
    user = app_settings.get("smtp_user")
    password = app_settings.get("smtp_password")
    from_addr = app_settings.get("smtp_from") or user

    if not host:
        logger.info("Email disabled (no smtp_host), skipping", to=to_addr)
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                if user:
                    server.login(user, password)
                server.sendmail(from_addr, [to_addr], message.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                if user:
                    server.login(user, password)
                server.sendmail(from_addr, [to_addr], message.as_string())
        logger.info("Digest email sent", to=to_addr, subject=subject)
        _log_email(to_addr, subject, "sent", digest_id=digest_id,
                   ruleset_id=ruleset_id, topic_name=topic_name, digest_type=digest_type)
    except Exception as e:
        logger.error("Failed to send digest email", to=to_addr, error=str(e))
        _log_email(to_addr, subject, "failed", error=str(e), digest_id=digest_id,
                   ruleset_id=ruleset_id, topic_name=topic_name, digest_type=digest_type)
        raise
