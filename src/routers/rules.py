"""
规则配置API路由
"""
from fastapi import APIRouter, HTTPException
import yaml
from pathlib import Path

from ..schemas.paper import RulesConfig, RulesUpdateRequest
from ..config import settings, rules_config

router = APIRouter()


@router.get("", response_model=RulesConfig)
async def get_rules():
    """获取当前规则配置"""
    config = rules_config.load()
    rules = config.get("rules", {})
    
    return RulesConfig(
        categories=rules.get("categories", []),
        keywords={
            "include": rules.get("keywords", {}).get("include", []),
            "exclude": rules.get("keywords", {}).get("exclude", [])
        },
        date_range=rules.get("date_range", 7),
        interests=rules.get("interests", ""),
        advanced={
            "authors": rules.get("advanced", {}).get("authors", []),
            "score_threshold": rules.get("advanced", {}).get("score_threshold", 5),
            "max_papers_per_fetch": rules.get("advanced", {}).get("max_papers_per_fetch", 100)
        },
        cost={
            "daily_token_limit": config.get("cost", {}).get("daily_token_limit", 0),
            "prefer_local_llm": config.get("cost", {}).get("prefer_local_llm", True)
        },
        s2_api_key=config.get("s2_api_key")
    )


@router.put("")
async def update_rules(request: RulesUpdateRequest):
    """更新规则配置"""
    config_path = settings.rules_config_path
    
    # 读取现有配置
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    # 更新rules部分
    rules_dict = request.rules.model_dump()
    config["rules"] = {
        "categories": rules_dict["categories"],
        "keywords": rules_dict["keywords"],
        "date_range": rules_dict["date_range"],
        "interests": rules_dict["interests"],
        "advanced": rules_dict["advanced"]
    }
    config["cost"] = rules_dict["cost"]
    
    if rules_dict.get("s2_api_key"):
        config["s2_api_key"] = rules_dict["s2_api_key"]
    
    # 保存配置
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    # 重新加载配置
    rules_config.reload()
    
    return {"status": "updated"}


@router.get("/categories")
async def get_arxiv_categories():
    """获取常用ArXiv分类列表"""
    return {
        "cs": {
            "cs.AI": "Artificial Intelligence",
            "cs.CL": "Computation and Language",
            "cs.CV": "Computer Vision",
            "cs.LG": "Machine Learning",
            "cs.NE": "Neural and Evolutionary Computing",
            "cs.RO": "Robotics",
            "cs.SE": "Software Engineering",
            "cs.DC": "Distributed Computing",
            "cs.PL": "Programming Languages"
        },
        "stat": {
            "stat.ML": "Machine Learning",
            "stat.TH": "Statistics Theory"
        },
        "eess": {
            "eess.AS": "Audio and Speech Processing",
            "eess.IV": "Image and Video Processing"
        }
    }
