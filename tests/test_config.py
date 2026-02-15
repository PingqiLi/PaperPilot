"""
配置模块单元测试
"""
import pytest
from pathlib import Path
import tempfile
import yaml

from src.config import Settings, RulesConfig


class TestSettings:
    """Settings 测试类"""

    def test_default_values(self):
        """测试默认配置值"""
        settings = Settings()
        
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.default_llm_backend == "ollama"
        assert settings.log_level == "INFO"

    def test_cors_origins_parsing(self):
        """测试CORS origins解析"""
        settings = Settings()
        
        assert isinstance(settings.cors_origins, list)


class TestRulesConfig:
    """RulesConfig 测试类"""

    def test_load_yaml(self):
        """测试YAML配置加载"""
        # 使用项目默认配置
        config_path = Path("config/rules.yaml")
        if config_path.exists():
            rules = RulesConfig(config_path)
            
            assert rules.categories is not None
            assert isinstance(rules.categories, list)

    def test_categories_property(self):
        """测试categories属性"""
        config_path = Path("config/rules.yaml")
        if config_path.exists():
            rules = RulesConfig(config_path)
            categories = rules.categories
            
            assert "cs.AI" in categories or "cs.LG" in categories

    def test_llm_config_property(self):
        """测试LLM配置获取"""
        config_path = Path("config/rules.yaml")
        if config_path.exists():
            rules = RulesConfig(config_path)
            llm_config = rules.llm_config
            
            assert isinstance(llm_config, dict)

    def test_custom_yaml_config(self):
        """测试自定义YAML配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "rules": {
                    "categories": ["cs.CV", "cs.RO"],
                    "keywords": {"include": ["robot"], "exclude": []},
                    "interests": "机器人视觉"
                },
                "llm": {"default_backend": "ollama"}
            }
            yaml.dump(config, f)
            f.flush()
            
            rules = RulesConfig(Path(f.name))
            
            assert rules.categories == ["cs.CV", "cs.RO"]
            assert rules.interests == "机器人视觉"
