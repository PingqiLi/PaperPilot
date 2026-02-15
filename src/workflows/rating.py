
"""
评分工作流 - 使用OpenClaw Agent评估论文相关性
"""
import json
import re
from typing import Dict, Any, Optional
from pathlib import Path
import structlog

from ..services.openclaw_client import OpenClawClient

logger = structlog.get_logger(__name__)

# Prompt模板路径
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "rating.md"

DEFAULT_PROMPT = """你是一个学术论文筛选助手。请根据用户的研究兴趣，评估论文的相关性。

## 用户研究兴趣
{interests}

## 待评估论文
**标题**: {title}

**摘要**: {abstract}

## 任务
请评估这篇论文与用户兴趣的相关性，评分范围1-10分：
- 1-3分：不相关或边缘相关
- 4-6分：有一定相关性
- 7-9分：高度相关
- 10分：完全匹配用户兴趣

## 输出格式
请以标准JSON格式输出，不要包含Markdown格式标记（如```json），只输出纯JSON字符串。包含以下字段：
{{
    "score": 8, 
    "reason": "一句话说明评分理由"
}}
"""


class RatingWorkflow:
    """评分工作流 (OpenClaw集成版)"""
    
    def __init__(self, client: OpenClawClient):
        self.client = client
        self._prompt_template = None
    
    def _load_prompt(self) -> str:
        """加载Prompt模板"""
        if self._prompt_template is None:
            if PROMPT_PATH.exists():
                self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
            else:
                self._prompt_template = DEFAULT_PROMPT
        return self._prompt_template
        
    def _clean_json_response(self, response: str) -> str:
        """清理并提取JSON字符串"""
        if not isinstance(response, str):
            return str(response)
            
        # 移除Markdown代码块标记
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
            
        return cleaned.strip()
    
    async def run(
        self,
        title: str,
        abstract: str,
        interests: str
    ) -> Dict[str, Any]:
        """
        执行评分工作流
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            interests: 用户兴趣描述
        
        Returns:
            {"score": int, "reason": str}
        """
        # 1. 准备任务描述
        prompt_template = self._load_prompt()
        task_message = prompt_template.format(
            title=title,
            abstract=abstract or "无摘要",
            interests=interests or "未指定研究兴趣"
        )
        
        try:
            # 2. 发送给OpenClaw Agent
            # 使用 wait=True 确保拿到最终结果
            # 使用 'dev' agent (或可配置)
            # 添加 extraSystemPrompt 强化 JSON 输出要求
            system_instruction = "You are a helpful assistant. Output must be strictly valid JSON."
            
            response = await self.client.send_agent_task(
                task=task_message,
                agent_id="dev",  # 默认使用 dev agent
                system_prompt=system_instruction,
                wait=True
            )
            
            # 3. 解析结果
            # OpenClaw 返回通常是字符串
            if isinstance(response, dict) and "response" in response:
                 # 某些agent可能包裹在 response 字段中
                 content = response["response"]
            else:
                 content = response
            
            # 如果content是字典（有些Agent直接返回结构化数据），直接使用
            if isinstance(content, dict):
                result = content
            else:
                cleaned_json = self._clean_json_response(str(content))
                result = json.loads(cleaned_json)
            
            # 4. 验证与格式化
            score = result.get("score", 5)
            if not isinstance(score, (int, float)):
                try:
                    score = float(score)
                except:
                    score = 5
            score = max(1, min(10, int(score)))
            
            reason = result.get("reason", "")
            
            return {"score": score, "reason": reason}
            
        except Exception as e:
            logger.error("Rating workflow failed", error=str(e))
            # 降级处理或返回默认值
            return {"score": 5, "reason": f"评分失败: {str(e)}"}
