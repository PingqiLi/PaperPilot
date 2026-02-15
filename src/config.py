"""
配置管理
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import yaml


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/paper_agent",
        description="PostgreSQL连接URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="允许的CORS来源"
    )
    
    # 规则配置文件路径
    rules_config_path: Path = Field(
        default=Path("config/rules.yaml"),
        description="规则配置文件路径"
    )
    
    # LLM配置
    openai_api_key: Optional[str] = Field(default=None)
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    ollama_base_url: str = Field(default="http://localhost:11434")
    vllm_base_url: str = Field(default="http://localhost:8000/v1")
    default_llm_backend: str = Field(default="ollama")
    default_llm_model: str = Field(default="qwen3-vl:8b")

    # Semantic Scholar
    s2_api_key: Optional[str] = Field(default=None)

    # OpenClaw
    openclaw_gateway_uri: str = Field(
        default="ws://127.0.0.1:19001",
        description="OpenClaw Gateway WebSocket URI"
    )
    openclaw_gateway_token: Optional[str] = Field(
        default=None,
        description="OpenClaw Gateway Authentication Token"
    )
    
    # 日志
    log_level: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class RulesConfig:
    """规则配置加载器"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = None
    
    def load(self) -> dict:
        """加载规则配置"""
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f)
            else:
                self._config = {}
        return self._config
    
    def reload(self) -> dict:
        """重新加载配置"""
        self._config = None
        return self.load()
    
    @property
    def categories(self) -> List[str]:
        config = self.load()
        return config.get("rules", {}).get("categories", [])
    
    @property
    def keywords_include(self) -> List[str]:
        config = self.load()
        return config.get("rules", {}).get("keywords", {}).get("include", [])
    
    @property
    def keywords_exclude(self) -> List[str]:
        config = self.load()
        return config.get("rules", {}).get("keywords", {}).get("exclude", [])
    
    @property
    def interests(self) -> str:
        config = self.load()
        return config.get("rules", {}).get("interests", "")
    
    @property
    def score_threshold(self) -> int:
        config = self.load()
        return config.get("rules", {}).get("advanced", {}).get("score_threshold", 5)
    
    @property
    def llm_config(self) -> dict:
        config = self.load()
        return config.get("llm", {})

    @property
    def s2_api_key(self) -> Optional[str]:
        config = self.load()
        return config.get("s2_api_key")


# 全局配置实例
settings = Settings()
rules_config = RulesConfig(settings.rules_config_path)
