"""
配置管理 - v1.0.0
SQLite + Qwen3.5-Plus (OpenAI-compatible API)
"""
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="sqlite:///data/paper_agent.db",
        description="SQLite数据库路径"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="允许的CORS来源"
    )

    # LLM配置 (Qwen3.5-Plus via Alibaba Cloud Bailian, OpenAI-compatible)
    llm_api_key: Optional[str] = Field(
        default=None,
        description="LLM API Key (Alibaba Cloud Bailian)"
    )
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="LLM API Base URL (OpenAI-compatible)"
    )
    llm_model: str = Field(
        default="qwen3.5-plus",
        description="LLM模型ID"
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="LLM最大输出token数"
    )
    llm_temperature: float = Field(
        default=0.3,
        description="LLM温度参数（低温=更确定性输出）"
    )

    # Semantic Scholar
    s2_api_key: Optional[str] = Field(default=None)

    # 日志
    log_level: str = Field(default="INFO")

    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="")
    digest_email_to: str = Field(default="")

    # 数据目录
    data_dir: Path = Field(
        default=Path("data"),
        description="数据存储目录"
    )




# 全局配置实例
settings = Settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)
