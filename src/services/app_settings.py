from typing import Any

from ..config import settings as env_settings
from ..database import SessionLocal
from ..models.app_setting import AppSetting

SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "llm_api_key": {"default": "", "secret": True, "category": "api", "label": "LLM API Key"},
    "llm_base_url": {"default": "https://dashscope.aliyuncs.com/compatible-mode/v1", "category": "api", "label": "LLM Base URL"},
    "llm_model": {"default": "qwen3.5-plus", "category": "api", "label": "LLM Model"},
    "llm_price_input": {"default": "0.8", "type": "float", "category": "api", "label": "Input Price (per M tokens)"},
    "llm_price_output": {"default": "4.8", "type": "float", "category": "api", "label": "Output Price (per M tokens)"},
    "s2_api_key": {"default": "", "secret": True, "category": "api", "label": "Semantic Scholar API Key"},

    "smtp_host": {"default": "", "category": "email", "label": "SMTP Host", "desc": "e.g. smtp.gmail.com"},
    "smtp_port": {"default": "587", "type": "int", "category": "email", "label": "SMTP Port", "desc": "587 for TLS, 465 for SSL"},
    "smtp_user": {"default": "", "category": "email", "label": "SMTP User", "desc": "Login username for SMTP server"},
    "smtp_password": {"default": "", "secret": True, "category": "email", "label": "SMTP Password"},
    "smtp_from": {"default": "", "category": "email", "label": "From Address", "desc": "Sender email shown in digest emails"},
    "digest_email_to": {"default": "", "category": "email", "label": "Recipient", "desc": "Email address to receive weekly/monthly digests"},

    "init_shortlist_size": {"default": "100", "type": "int", "category": "pipeline", "label": "Initialize Papers Count", "desc": "Number of top papers to LLM-score during topic initialization"},
    "init_max_surveys": {"default": "2", "type": "int", "category": "pipeline", "label": "Max Surveys in Initialize", "desc": "Keep up to N survey papers for foundational reading"},
    "track_top_n": {"default": "20", "type": "int", "category": "pipeline", "label": "Track Top-N", "desc": "Daily tracking selects top N candidates for LLM scoring"},
    "track_min_score": {"default": "7", "type": "int", "category": "pipeline", "label": "Track Min Score", "desc": "Tracked papers scored below this are discarded (higher bar than Init)"},
    "display_top_n": {"default": "30", "type": "int", "category": "pipeline", "label": "Display Top-N", "desc": "Default number of papers shown per page, sorted by LLM score"},
    "highlight_threshold": {"default": "7", "type": "int", "category": "pipeline", "label": "Highlight Score Threshold", "desc": "Papers scored >= this appear on the homepage highlights"},
    "arxiv_max_papers": {"default": "300", "type": "int", "category": "pipeline", "label": "ArXiv Max Papers", "desc": "Maximum papers to fetch from ArXiv boolean search per topic (newest first if over limit)"},
    "scoring_batch_size": {"default": "10", "type": "int", "category": "pipeline", "label": "Scoring Batch Size", "desc": "Papers per LLM scoring call (max ~15, higher = fewer calls)"},
    "scoring_concurrency": {"default": "5", "type": "int", "category": "pipeline", "label": "Scoring Concurrency", "desc": "Parallel LLM scoring calls (higher = faster init, more API pressure)"},
    "min_score_to_keep": {"default": "6", "type": "int", "category": "pipeline", "label": "Min Score to Keep", "desc": "Papers scored below this threshold are discarded after LLM scoring (Paper record kept, topic association removed)"},
    "currency": {"default": "CNY", "category": "pipeline", "label": "Currency", "desc": "Currency for cost display and budget (CNY, USD, EUR, GBP, JPY, KRW)"},
    "monthly_budget_cap": {"default": "30", "type": "float", "category": "pipeline", "label": "Monthly Budget Cap", "desc": "LLM calls stop when monthly cost reaches this limit"},

    "output_language": {"default": "中文", "category": "prompts", "label": "Output Language", "desc": "Language for LLM-generated text (scoring reasons, digests, analysis)"},
    "prompt_batch_scoring_rubric": {"default": "", "type": "text", "category": "prompts", "label": "Scoring Criteria", "desc": "Customize the 1-10 scoring rubric and metadata signal weights"},
    "prompt_field_overview": {"default": "", "type": "text", "category": "prompts", "label": "Field Overview", "desc": "Prompt for generating field overview digests"},
    "prompt_weekly_digest": {"default": "", "type": "text", "category": "prompts", "label": "Weekly Digest", "desc": "Prompt for generating weekly research digests"},
    "prompt_monthly_report": {"default": "", "type": "text", "category": "prompts", "label": "Monthly Report", "desc": "Prompt for generating monthly trend reports"},
    "prompt_paper_analysis": {"default": "", "type": "text", "category": "prompts", "label": "Paper Analysis", "desc": "Prompt for generating deep-dive paper analysis"},

    "schedule_track_cron": {"default": "0 0 * * 0", "category": "schedule", "label": "Track Schedule"},
    "schedule_weekly_cron": {"default": "0 9 * * 1", "category": "schedule", "label": "Weekly Digest Cron"},
    "schedule_monthly_cron": {"default": "0 10 1 * *", "category": "schedule", "label": "Monthly Report Cron"},
    "schedule_timezone": {"default": "Asia/Shanghai", "category": "schedule", "label": "Timezone"},
    "schedule_enabled": {"default": "true", "type": "bool", "category": "schedule", "label": "Enable Scheduler"},
}

_ENV_ATTRS = {
    "llm_api_key", "llm_base_url", "llm_model", "llm_max_tokens", "llm_temperature",
    "s2_api_key", "smtp_host", "smtp_port", "smtp_user", "smtp_password",
    "smtp_from", "digest_email_to",
}


def _mask_secret(value: str) -> str:
    if not value or len(value) <= 4:
        return "****" if value else ""
    return "*" * (len(value) - 4) + value[-4:]


def get(key: str) -> str:
    schema = SETTINGS_SCHEMA.get(key)

    db = SessionLocal()
    try:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row and row.value is not None and str(row.value) != "":
            return str(row.value)
    finally:
        db.close()

    if key in _ENV_ATTRS:
        env_val = getattr(env_settings, key, None)
        if env_val is not None and str(env_val) != "":
            return str(env_val)

    return schema["default"] if schema else ""


def get_int(key: str) -> int:
    try:
        return int(get(key))
    except (ValueError, TypeError):
        schema = SETTINGS_SCHEMA.get(key, {})
        return int(schema.get("default", "0"))


def get_float(key: str) -> float:
    try:
        return float(get(key))
    except (ValueError, TypeError):
        schema = SETTINGS_SCHEMA.get(key, {})
        return float(schema.get("default", "0"))


def get_bool(key: str) -> bool:
    return get(key).lower() in ("true", "1", "yes")


def set_many(updates: dict[str, Any]):
    db = SessionLocal()
    try:
        for key, value in updates.items():
            if key not in SETTINGS_SCHEMA:
                continue
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            str_val = str(value) if value is not None else ""
            if row:
                row.value = str_val
            else:
                db.add(AppSetting(key=key, value=str_val))
        db.commit()
    finally:
        db.close()


def get_all() -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for key, schema in SETTINGS_SCHEMA.items():
        category = schema["category"]
        if category not in grouped:
            grouped[category] = {}

        value = get(key)
        display_value = _mask_secret(value) if schema.get("secret") else value

        entry = {
            "value": display_value,
            "label": schema["label"],
            "type": schema.get("type", "str"),
            "secret": schema.get("secret", False),
        }
        if schema.get("desc"):
            entry["desc"] = schema["desc"]
        grouped[category][key] = entry
    return grouped
