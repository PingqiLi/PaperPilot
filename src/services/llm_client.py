"""
LLM客户端 - 通过OpenAI-compatible API调用Qwen3.5-Plus
"""
import json
import os
from datetime import datetime
from typing import Any, Optional

import httpx
import structlog
from sqlalchemy import func
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..database import get_db_context
from ..models import TokenUsage
from . import app_settings
from .t2s import convert as t2s

logger = structlog.get_logger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_prompt(name: str) -> str:
    custom = app_settings.get(f"prompt_{name}")
    if custom:
        return custom
    return load_prompt(f"{name}.md")


def _clean_json_response(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0]
    return cleaned.strip()


_RETRYABLE = (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)
_SKIP_LANGUAGE_WORKFLOWS = frozenset({"draft_generation"})


class BudgetExceededError(Exception):
    pass


class LLMClient:
    _CONFIG_TTL = 30

    def __init__(self):
        self._config_cache: dict[str, Any] = {}
        self._config_ts: float = 0
        self._budget_cache: Optional[float] = None
        self._budget_ts: float = 0
        self._http_client: Optional[httpx.AsyncClient] = None

    def _load_config(self):
        import time
        now = time.monotonic()
        if now - self._config_ts < self._CONFIG_TTL and self._config_cache:
            return
        self._config_cache = {
            "base_url": app_settings.get("llm_base_url").rstrip("/"),
            "api_key": app_settings.get("llm_api_key"),
            "model": app_settings.get("llm_model"),
            "max_tokens": app_settings.get_int("llm_max_tokens") or 4096,
            "temperature": app_settings.get_float("llm_temperature") or 0.3,
        }
        self._config_ts = now

    def _cfg(self, key: str) -> Any:
        self._load_config()
        return self._config_cache[key]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=300.0)
        return self._http_client

    def _check_budget(self):
        import time
        now = time.monotonic()
        if now - self._budget_ts < 10 and self._budget_cache is not None:
            cap = app_settings.get_float("monthly_budget_cap")
            if cap > 0 and self._budget_cache >= cap:
                raise BudgetExceededError(
                    f"月度预算已用完 ({self._budget_cache:.2f}/{cap:.2f} CNY)，LLM 调用已暂停"
                )
            return
        cap = app_settings.get_float("monthly_budget_cap")
        if cap <= 0:
            return
        dt_now = datetime.utcnow()
        start_of_month = datetime(dt_now.year, dt_now.month, 1)
        try:
            with get_db_context() as db:
                row = db.query(func.sum(TokenUsage.cost_yuan)).filter(
                    TokenUsage.timestamp >= start_of_month
                ).scalar()
                self._budget_cache = float(row or 0)
                self._budget_ts = now
        except Exception:
            return
        if self._budget_cache >= cap:
            raise BudgetExceededError(
                f"月度预算已用完 ({self._budget_cache:.2f}/{cap:.2f} CNY)，LLM 调用已暂停"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type(_RETRYABLE),
        before_sleep=lambda rs: structlog.get_logger().warning(
            "LLM call retry",
            attempt=rs.attempt_number,
            wait=rs.next_action.sleep,
            error=str(rs.outcome.exception()) if rs.outcome else "unknown",
        ),
    )
    async def chat(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        workflow: str = "chat",
    ) -> str:
        self._check_budget()

        if workflow not in _SKIP_LANGUAGE_WORKFLOWS:
            lang = app_settings.get("output_language")
            if lang:
                lang_directive = f"IMPORTANT: All text output MUST be in {lang}.\n\n"
                if system_message:
                    system_message = lang_directive + system_message
                else:
                    user_message = lang_directive + user_message

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        payload: dict[str, Any] = {
            "model": self._cfg("model"),
            "messages": messages,
            "temperature": temperature if temperature is not None else self._cfg("temperature"),
            "max_tokens": max_tokens or self._cfg("max_tokens"),
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._cfg('api_key')}",
        }

        client = await self._get_client()
        resp = await client.post(
            f"{self._cfg('base_url')}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        self._track_usage(usage, workflow=workflow, model=self._cfg("model"))

        return t2s(content)

    async def chat_json(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        workflow: str = "chat",
    ) -> dict:
        raw = await self.chat(
            user_message=user_message,
            system_message=system_message or "Output must be strictly valid JSON.",
            response_format="json",
            workflow=workflow,
        )
        cleaned = _clean_json_response(raw)
        return json.loads(cleaned)

    def _track_usage(self, usage: dict, workflow: str = "chat", model: str = ""):
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if input_tokens == 0 and output_tokens == 0:
            return

        price_input = app_settings.get_float("llm_price_input")
        price_output = app_settings.get_float("llm_price_output")
        cost = (
            (input_tokens / 1_000_000) * price_input
            + (output_tokens / 1_000_000) * price_output
        )

        try:
            with get_db_context() as db:
                record = TokenUsage(
                    model=model or self._cfg("model"),
                    workflow=workflow,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_yuan=cost,
                )
                db.add(record)
        except Exception as e:
            logger.error("Failed to track token usage", error=str(e))


llm_client = LLMClient()
