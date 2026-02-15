
"""
信息抽取工作流 - 使用OpenClaw Agent从论文中抽取结构化信息
"""
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

from ..services.openclaw_client import OpenClawClient

logger = structlog.get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extraction.md"

DEFAULT_PROMPT = """你是一个学术论文分析助手。请从论文中抽取关键信息。

## 论文信息
**标题**: {title}

**摘要**: {abstract}

**全文内容**（如有）:
{content}

## 任务
请从论文中抽取以下结构化信息：
1. **关键词**: 论文的关键词或主题词
2. **数据集**: 论文中使用的数据集
3. **基线方法**: 论文对比的基线方法
4. **评估指标**: 论文使用的评估指标及结果
5. **代码/模型**: 是否开源代码或模型

## 输出格式
请以标准JSON格式输出，不要包含Markdown格式标记（如```json），只输出纯JSON字符串。包含以下字段：
{{
  "keywords": ["关键词1", "关键词2"],
  "datasets": ["数据集1", "数据集2"],
  "baselines": ["基线方法1", "基线方法2"],
  "metrics": {{
    "指标名": "结果值"
  }},
  "code_available": true,
  "code_url": "https://github.com/..."
}}

如果某项信息在论文中未找到，请使用空列表或空字符串。只输出JSON。"""


class ExtractionWorkflow:
    """信息抽取工作流 (OpenClaw集成版)"""
    
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
    
    def _truncate_content(self, content: str, max_tokens: int = 4000) -> str:
        """截断过长内容"""
        # 粗略估计
        max_chars = max_tokens * 2
        if content and len(content) > max_chars:
            return content[:max_chars] + "\n\n[内容已截断...]"
        return content or "无全文内容"
        
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
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行信息抽取工作流
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            content: 论文全文（可选）
        
        Returns:
            抽取的结构化信息
        """
        prompt_template = self._load_prompt()
        
        truncated_content = self._truncate_content(content)
        
        task_message = prompt_template.format(
            title=title,
            abstract=abstract or "无摘要",
            content=truncated_content
        )
        
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
                "keywords": result.get("keywords", []),
                "datasets": result.get("datasets", []),
                "baselines": result.get("baselines", []),
                "metrics": result.get("metrics", {}),
                "code_available": result.get("code_available", False),
                "code_url": result.get("code_url", "")
            }
            
        except Exception as e:
            logger.error("Extraction workflow failed", error=str(e))
            return {
                "keywords": [],
                "datasets": [],
                "baselines": [],
                "metrics": {},
                "code_available": False,
                "code_url": ""
            }
