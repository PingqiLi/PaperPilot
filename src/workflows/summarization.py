
"""
摘要工作流 - 使用OpenClaw Agent生成论文摘要
"""
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

from ..services.openclaw_client import OpenClawClient

logger = structlog.get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "summary.md"

DEFAULT_PROMPT = """你是一个学术论文分析助手。请总结以下论文内容。

## 论文内容
{content}

## 任务
请生成结构化的论文摘要，包含以下部分：
1. **核心贡献**: 用一句话概括论文的主要贡献
2. **方法**: 简述所用的技术方法（2-3句话）
3. **主要结果**: 关键实验结果和发现
4. **关键发现**: 列出3-5个关键发现点
5. **局限性**: 作者提到的局限性（如有）

## 输出格式
请以标准JSON格式输出，不要包含Markdown格式标记（如```json），只输出纯JSON字符串。包含以下字段：
{{
  "summary": "核心贡献的一句话概括",
  "methodology": "技术方法简述",
  "main_results": "主要结果描述",
  "key_findings": ["发现1", "发现2", "发现3"],
  "limitations": "局限性描述（如无则为空字符串）"
}}
"""


class SummarizationWorkflow:
    """摘要工作流 (OpenClaw集成版)"""
    
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
    
    def _truncate_content(self, content: str, max_tokens: int = 6000) -> str:
        """截断过长内容（粗略估计）"""
        # 粗略估计：1个token约等于4个字符（中文约2个字符）
        max_chars = max_tokens * 2
        if len(content) > max_chars:
            return content[:max_chars] + "\n\n[内容已截断...]"
        return content
        
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
    
    async def run(self, content: str) -> Dict[str, Any]:
        """
        执行摘要工作流
        
        Args:
            content: 论文内容（Markdown或纯文本）
        
        Returns:
            {"summary": str, "methodology": str, "main_results": str, 
             "key_findings": List[str], "limitations": str}
        """
        prompt_template = self._load_prompt()
        
        # 截断过长内容
        truncated_content = self._truncate_content(content)
        
        task_message = prompt_template.format(content=truncated_content)
        
        try:
            # 发送给OpenClaw Agent
            system_instruction = "You are a helpful assistant. Output must be strictly valid JSON."
            
            response = await self.client.send_agent_task(
                task=task_message,
                agent_id="dev",  # 默认使用 dev agent
                system_prompt=system_instruction,
                wait=True
            )
            
            # 解析结果
            # OpenClaw 返回通常是字符串
            if isinstance(response, dict) and "response" in response:
                 content = response["response"]
            else:
                 content = response
            
            if isinstance(content, dict):
                result = content
            else:
                cleaned_json = self._clean_json_response(str(content))
                result = json.loads(cleaned_json)
            
            return {
                "summary": result.get("summary", ""),
                "methodology": result.get("methodology", ""),
                "main_results": result.get("main_results", ""),
                "key_findings": result.get("key_findings", []),
                "limitations": result.get("limitations", "")
            }
            
        except Exception as e:
            logger.error("Summarization workflow failed", error=str(e))
            return {
                "summary": f"摘要生成失败: {str(e)}",
                "methodology": "",
                "main_results": "",
                "key_findings": [],
                "limitations": ""
            }
