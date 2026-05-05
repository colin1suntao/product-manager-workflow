"""OpenAI适配器"""

import os
from typing import Any, AsyncGenerator, Optional

import httpx
from pm_workstation.model_router.base import LLMBackend, LLMConfig, LLMMessage, LLMResponse


class OpenAIAdapter(LLMBackend):
    """OpenAI LLM适配器"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is None:
            from openai import AsyncOpenAI
            
            # 配置 HTTP 客户端，支持代理和超时
            timeout = httpx.Timeout(
                connect=30.0,
                read=120.0,
                write=30.0,
                pool=30.0,
            )
            
            # 构建 proxy 配置
            proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
            
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": timeout,
            }
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            if proxy_url:
                client_kwargs["http_client"] = httpx.AsyncClient(proxy=proxy_url, timeout=timeout)
            
            self._client = AsyncOpenAI(**client_kwargs)
        
        return self._client
    
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """发送聊天请求到OpenAI"""
        client = self._get_client()
        
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            **kwargs,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """发送流式聊天请求到OpenAI"""
        client = self._get_client()
        
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        stream = await client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            stream=True,
            **kwargs,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return f"openai:{self.config.model}"
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return bool(self.config.api_key)
