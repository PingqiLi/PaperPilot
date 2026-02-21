"""
Topic草案自动生成 - 用户输入主题句，LLM生成完整规则集草案
"""
import json

import structlog

from .llm_client import llm_client, load_prompt

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = load_prompt("draft_generation.md")


async def generate_draft(topic_sentence: str) -> dict:
    try:
        result = await llm_client.chat_json(
            user_message=f"Topic: {topic_sentence}",
            system_message=_SYSTEM_PROMPT,
            workflow="draft_generation",
        )
    except json.JSONDecodeError as e:
        logger.error("Draft generation JSON parse failed", topic=topic_sentence, error=str(e))
        raise ValueError(f"LLM返回内容无法解析为JSON: {e}")
    except Exception as e:
        logger.error("Draft generation failed", topic=topic_sentence, error=str(e))
        raise

    return {
        "name": result.get("name", "Untitled"),
        "topic_sentence": topic_sentence,
        "categories": result.get("categories", []),
        "keywords_include": result.get("keywords_include", []),
        "keywords_exclude": result.get("keywords_exclude", []),
        "search_queries": result.get("search_queries", []),
        "method_queries": result.get("method_queries", []),
    }
