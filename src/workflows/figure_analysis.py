"""
图表分析工作流 - 使用VL模型分析论文图表
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "figure_analysis.md"

DEFAULT_PROMPT = """你是一个学术论文分析助手。请分析以下论文中的图表。

## 论文背景
**标题**: {title}
**摘要**: {abstract}

## 任务
请分析图中的内容，识别：
1. 图表类型（表格/折线图/柱状图/架构图/热力图等）
2. 关键数据点或结构
3. 主要发现或结论

## 输出格式
请以JSON格式输出：
```json
{{
  "figure_type": "性能对比表",
  "key_data": ["方法A准确率92.5%", "方法B准确率89.1%"],
  "insights": ["提出的方法在所有指标上优于基线"],
  "importance": "high"
}}
```

只输出JSON，不要其他内容。"""


class FigureAnalysisWorkflow:
    """图表分析工作流（使用VL模型）"""
    
    def __init__(self, llm_service):
        self.llm = llm_service
        self._prompt_template = None
    
    def _load_prompt(self) -> str:
        """加载Prompt模板"""
        if self._prompt_template is None:
            if PROMPT_PATH.exists():
                self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
            else:
                self._prompt_template = DEFAULT_PROMPT
        return self._prompt_template
    
    async def run(
        self,
        figures: List[Dict[str, Any]],
        title: str,
        abstract: str
    ) -> Dict[str, Any]:
        """
        分析论文图表
        
        Args:
            figures: 图表列表 [{"base64": "...", "page": 1, ...}]
            title: 论文标题
            abstract: 论文摘要
        
        Returns:
            {"analyses": [...], "summary": str}
        """
        if not figures:
            return {"analyses": [], "summary": "无图表可分析"}
        
        prompt_template = self._load_prompt()
        prompt = prompt_template.format(
            title=title,
            abstract=abstract or "无摘要"
        )
        
        # 提取base64图像列表
        images = [f["base64"] for f in figures if f.get("base64")]
        
        if not images:
            return {"analyses": [], "summary": "无有效图表"}
        
        try:
            # 调用VL模型
            result = await self.llm.generate_json(
                prompt=prompt,
                images=images,  # VL多模态
                temperature=0.3,
                max_tokens=800
            )
            
            # 处理单图或多图结果
            if isinstance(result, list):
                analyses = result
            else:
                analyses = [result]
            
            # 生成摘要
            high_importance = [a for a in analyses if a.get("importance") == "high"]
            summary = f"分析了{len(figures)}张图表"
            if high_importance:
                summary += f"，其中{len(high_importance)}张为关键图表"
            
            return {
                "analyses": analyses,
                "summary": summary,
                "figure_count": len(figures)
            }
            
        except Exception as e:
            logger.error("Figure analysis failed", error=str(e))
            return {
                "analyses": [],
                "summary": f"图表分析失败: {str(e)}",
                "figure_count": len(figures)
            }
    
    async def analyze_single(
        self,
        image_base64: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """分析单张图表"""
        prompt = f"""分析这张学术论文中的图表。
        
上下文：{context or "无"}

识别图表类型、关键数据、主要发现。
输出JSON: {{"figure_type": "...", "key_data": [...], "insights": [...]}}"""
        
        try:
            return await self.llm.generate_json(
                prompt=prompt,
                images=[image_base64],
                temperature=0.3,
                max_tokens=500
            )
        except Exception as e:
            logger.error("Single figure analysis failed", error=str(e))
            return {"error": str(e)}
