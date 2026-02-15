"""
LLM服务 - 统一接口支持OpenAI/Ollama/vLLM
"""
import json
import base64
from typing import Optional, Dict, Any, Union, List
from abc import ABC, abstractmethod
import httpx
import structlog

from ..config import settings, rules_config

logger = structlog.get_logger(__name__)


class LLMBackend(ABC):
    """LLM后端抽象基类"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        images: Optional[List[str]] = None
    ) -> str:
        """生成文本（支持多模态图像输入）
        
        Args:
            images: base64编码的图像列表（用于VL模型）
        """
        pass


class OpenAIBackend(LLMBackend):
    """OpenAI兼容API后端"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        images: Optional[List[str]] = None
    ) -> str:
        # OpenAI VL模型使用content数组格式
        # 当前实现仅支持文本，VL需使用Ollama后端
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            request_body["response_format"] = {"type": "json_object"}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class OllamaBackend(LLMBackend):
    """Ollama本地部署后端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        images: Optional[List[str]] = None
    ) -> str:
        """生成文本（支持VL多模态）
        
        Args:
            images: base64编码的图像列表（用于qwen3-vl等VL模型）
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        request_body = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # VL多模态：添加图像
        if images:
            request_body["images"] = images
        
        if json_mode:
            request_body["format"] = "json"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=request_body
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]


class VLLMBackend(LLMBackend):
    """vLLM部署后端（OpenAI兼容API）"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-7B-Instruct"
    ):
        self.api_key = "EMPTY"  # vLLM不需要真实API key
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        images: Optional[List[str]] = None
    ) -> str:
        # 复用OpenAI兼容接口
        backend = OpenAIBackend(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )
        return await backend.generate(
            prompt, system_prompt, temperature, max_tokens, json_mode, images
        )


class LLMService:
    """LLM服务统一入口"""
    
    def __init__(self):
        self._backends: Dict[str, LLMBackend] = {}
        self._default_backend: Optional[str] = None
        self._init_backends()
    
    def _init_backends(self):
        """初始化后端"""
        llm_config = rules_config.llm_config
        
        # OpenAI
        if settings.openai_api_key:
            openai_config = llm_config.get("openai", {})
            self._backends["openai"] = OpenAIBackend(
                api_key=settings.openai_api_key,
                base_url=openai_config.get("base_url", settings.openai_base_url),
                model=openai_config.get("model", "gpt-4o-mini")
            )
        
        # Ollama
        ollama_config = llm_config.get("ollama", {})
        self._backends["ollama"] = OllamaBackend(
            base_url=ollama_config.get("base_url", settings.ollama_base_url),
            model=ollama_config.get("model", settings.default_llm_model)
        )
        
        # vLLM
        vllm_config = llm_config.get("vllm", {})
        self._backends["vllm"] = VLLMBackend(
            base_url=vllm_config.get("base_url", settings.vllm_base_url),
            model=vllm_config.get("model", "Qwen/Qwen2.5-7B-Instruct")
        )
        
        # 设置默认后端
        self._default_backend = llm_config.get("default_backend", settings.default_llm_backend)
    
    def get_backend(self, name: Optional[str] = None) -> LLMBackend:
        """获取LLM后端"""
        backend_name = name or self._default_backend
        if backend_name not in self._backends:
            raise ValueError(f"Unknown backend: {backend_name}")
        return self._backends[backend_name]
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        backend: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> str:
        """生成文本（支持VL多模态图像输入）"""
        llm_backend = self.get_backend(backend)
        
        logger.debug(
            "LLM generate",
            backend=backend or self._default_backend,
            prompt_length=len(prompt)
        )
        
        try:
            result = await llm_backend.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                images=images
            )
            logger.debug("LLM response", response_length=len(result), has_images=bool(images))
            return result
        except Exception as e:
            logger.error("LLM error", error=str(e))
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        backend: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """生成JSON并解析（支持VL多模态）"""
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            backend=backend,
            images=images
        )
        
        # 尝试解析JSON
        try:
            # 处理可能的markdown代码块
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            return json.loads(result.strip())
        except json.JSONDecodeError as e:
            logger.error("JSON parse error", response=result[:200], error=str(e))
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")


# 全局服务实例
llm_service = LLMService()
