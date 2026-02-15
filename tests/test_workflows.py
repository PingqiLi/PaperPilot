
"""
工作流单元测试 (OpenClaw集成版)
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.workflows.rating import RatingWorkflow
from src.workflows.summarization import SummarizationWorkflow
from src.workflows.extraction import ExtractionWorkflow
from src.services.openclaw_client import OpenClawClient


class TestRatingWorkflow:
    """评分工作流测试"""

    def test_load_prompt(self):
        """测试Prompt模板加载"""
        mock_client = MagicMock(spec=OpenClawClient)
        workflow = RatingWorkflow(mock_client)
        
        prompt = workflow._load_prompt()
        
        assert "用户研究兴趣" in prompt
        assert "{title}" in prompt
        assert "{abstract}" in prompt
        assert "通过OpenClaw" not in prompt # 确保没有残留

    def test_clean_json_response(self):
        """测试JSON清洗功能"""
        mock_client = MagicMock(spec=OpenClawClient)
        workflow = RatingWorkflow(mock_client)
        
        # Case 1: Pure JSON
        raw = '{"score": 8, "reason": "test"}'
        assert workflow._clean_json_response(raw) == raw
        
        # Case 2: Markdown fence
        raw = '```json\n{"score": 8}\n```'
        assert workflow._clean_json_response(raw) == '{"score": 8}'
        
        # Case 3: Markdown fence without language
        raw = '```\n{"score": 8}\n```'
        assert workflow._clean_json_response(raw) == '{"score": 8}'

    @pytest.mark.asyncio
    async def test_run_success(self):
        """测试成功评分"""
        mock_client = MagicMock(spec=OpenClawClient)
        # Mock send_agent_task returning a JSON string (as OpenClaw often does)
        mock_client.send_agent_task = AsyncMock(return_value=json.dumps({
            "score": 8,
            "reason": "高度相关，涉及量化优化"
        }))
        
        workflow = RatingWorkflow(mock_client)
        result = await workflow.run(
            title="LLM Quantization",
            abstract="INT4 quantization for inference",
            interests="大模型推理优化"
        )
        
        assert result["score"] == 8
        assert "reason" in result
        
        # Verify call arguments
        call_args = mock_client.send_agent_task.call_args[1]
        assert "LLM Quantization" in call_args["task"]
        assert call_args["agent_id"] == "dev"
        assert call_args["wait"] is True

    @pytest.mark.asyncio
    async def test_run_with_dict_response(self):
        """测试直接返回字典的情况"""
        mock_client = MagicMock(spec=OpenClawClient)
        # Mock returning a dict directly
        mock_client.send_agent_task = AsyncMock(return_value={
            "score": 9,
            "reason": "Direct dict"
        })
        
        workflow = RatingWorkflow(mock_client)
        result = await workflow.run("Title", "Abstract", "Interests")
        
        assert result["score"] == 9
        assert result["reason"] == "Direct dict"

    @pytest.mark.asyncio
    async def test_run_score_validation(self):
        """测试评分范围验证"""
        mock_client = MagicMock(spec=OpenClawClient)
        mock_client.send_agent_task = AsyncMock(return_value=json.dumps({
            "score": 15,  # 超出1-10范围
            "reason": "测试"
        }))
        
        workflow = RatingWorkflow(mock_client)
        result = await workflow.run("Title", "Abstract", "Interests")
        
        # 应该被约束到10
        assert result["score"] == 10

    @pytest.mark.asyncio
    async def test_run_error_handling(self):
        """测试错误处理"""
        mock_client = MagicMock(spec=OpenClawClient)
        mock_client.send_agent_task = AsyncMock(side_effect=Exception("Gateway Timeout"))
        
        workflow = RatingWorkflow(mock_client)
        result = await workflow.run("Title", "Abstract", "Interests")
        
        # 应该返回默认值
        assert result["score"] == 5
        assert "评分失败" in result["reason"]


class TestSummarizationWorkflow:
    """摘要工作流测试"""

    @pytest.mark.asyncio
    async def test_run_success(self):
        """测试成功摘要"""
        mock_client = MagicMock(spec=OpenClawClient)
        mock_client.send_agent_task = AsyncMock(return_value=json.dumps({
            "summary": "提出了一种新的量化方法",
            "methodology": "使用INT4量化",
            "main_results": "加速2倍",
            "key_findings": ["发现1", "发现2"],
            "limitations": "精度略有下降"
        }))
        
        workflow = SummarizationWorkflow(mock_client)
        result = await workflow.run("论文内容...")
        
        assert "量化" in result["summary"]
        assert len(result["key_findings"]) == 2
        
        # Verify content truncation logic (implicit)
        call_args = mock_client.send_agent_task.call_args[1]
        assert "论文内容" in call_args["task"]

    @pytest.mark.asyncio
    async def test_run_malformed_json(self):
        """测试返回非JSON字符串"""
        mock_client = MagicMock(spec=OpenClawClient)
        mock_client.send_agent_task = AsyncMock(return_value="Not a JSON string")
        
        workflow = SummarizationWorkflow(mock_client)
        result = await workflow.run("Content")
        
        assert "摘要生成失败" in result["summary"]


class TestExtractionWorkflow:
    """信息抽取工作流测试"""

    @pytest.mark.asyncio
    async def test_run_success(self):
        """测试成功抽取"""
        mock_client = MagicMock(spec=OpenClawClient)
        mock_client.send_agent_task = AsyncMock(return_value=json.dumps({
            "keywords": ["quantization", "LLM", "inference"],
            "datasets": ["WikiText", "C4"],
            "baselines": ["GPTQ", "AWQ"],
            "metrics": {"Perplexity": "5.2", "Speedup": "2x"},
            "code_available": True,
            "code_url": "https://github.com/example/repo"
        }))
        
        workflow = ExtractionWorkflow(mock_client)
        result = await workflow.run(
            title="Test Paper",
            abstract="Test abstract",
            content="Full content..."
        )
        
        assert "quantization" in result["keywords"]
        assert result["code_available"] is True
        assert "github.com" in result["code_url"]
