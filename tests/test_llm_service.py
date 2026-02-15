"""
LLM服务单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.services.llm_service import (
    LLMBackend,
    OllamaBackend,
    OpenAIBackend,
    LLMService
)


class TestOllamaBackend:
    """Ollama后端测试"""

    def test_init(self):
        """测试初始化"""
        backend = OllamaBackend(
            base_url="http://localhost:11434",
            model="qwen3-vl:8b"
        )
        
        assert backend.base_url == "http://localhost:11434"
        assert backend.model == "qwen3-vl:8b"

    @pytest.mark.asyncio
    async def test_generate_text(self):
        """测试文本生成（需要Ollama运行）"""
        backend = OllamaBackend(model="qwen3-vl:8b")
        
        # Mock httpx客户端
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Hello, world!"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await backend.generate("Say hello")
            
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_generate_with_images(self):
        """测试多模态生成（VL模型）"""
        backend = OllamaBackend(model="qwen3-vl:8b")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "I see a figure"}
            mock_response.raise_for_status = MagicMock()
            
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.post = AsyncMock(return_value=mock_response)
            
            result = await backend.generate(
                prompt="Describe this image",
                images=["base64_encoded_image"]
            )
            
            assert result == "I see a figure"
            
            # 验证images参数被传递
            call_args = mock_instance.post.call_args
            request_body = call_args.kwargs.get('json', {})
            assert "images" in request_body


class TestLLMService:
    """LLM服务测试"""

    def test_get_backend_ollama(self):
        """测试获取Ollama后端"""
        with patch.object(LLMService, '_init_backends'):
            service = LLMService()
            service._backends = {"ollama": OllamaBackend()}
            service._default_backend = "ollama"
            
            backend = service.get_backend("ollama")
            
            assert isinstance(backend, OllamaBackend)

    def test_get_backend_invalid(self):
        """测试获取无效后端"""
        with patch.object(LLMService, '_init_backends'):
            service = LLMService()
            service._backends = {}
            
            with pytest.raises(ValueError, match="Unknown backend"):
                service.get_backend("invalid")

    @pytest.mark.asyncio
    async def test_generate_json_parse(self):
        """测试JSON解析"""
        with patch.object(LLMService, '_init_backends'):
            service = LLMService()
            mock_backend = MagicMock()
            mock_backend.generate = AsyncMock(
                return_value='{"score": 8, "reason": "Good"}'
            )
            service._backends = {"ollama": mock_backend}
            service._default_backend = "ollama"
            
            result = await service.generate_json("Test prompt")
            
            assert result["score"] == 8
            assert result["reason"] == "Good"

    @pytest.mark.asyncio
    async def test_generate_json_markdown_cleanup(self):
        """测试JSON从markdown代码块提取"""
        with patch.object(LLMService, '_init_backends'):
            service = LLMService()
            mock_backend = MagicMock()
            # 模拟LLM返回带markdown的JSON
            mock_backend.generate = AsyncMock(
                return_value='```json\n{"value": 42}\n```'
            )
            service._backends = {"ollama": mock_backend}
            service._default_backend = "ollama"
            
            result = await service.generate_json("Test")
            
            assert result["value"] == 42
