"""Anthropic适配器"""

import os
from typing import Any, AsyncGenerator, Optional

import httpx
from pm_workstation.model_router.base import LLMBackend, LLMConfig, LLMMessage, LLMResponse


class AnthropicAdapter(LLMBackend):
    """Anthropic Claude LLM适配器"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """获取Anthropic客户端"""
        if self._client is None:
            from anthropic import AsyncAnthropic
            
            # 配置 HTTP 客户端，支持代理和超时
            # 生成任务（原型/PRD）可能需要 5-10 分钟，read 超时设长
            timeout = httpx.Timeout(
                connect=30.0,
                read=600.0,
                write=30.0,
                pool=60.0,
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
            
            self._client = AsyncAnthropic(**client_kwargs)
        
        return self._client
    
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """发送聊天请求到Anthropic"""
        client = self._get_client()
        
        # Anthropic API需要分离system消息
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        response = await client.messages.create(
            model=self.config.model,
            system=system_message,
            messages=chat_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            **kwargs,
        )
        
        return LLMResponse(
            content=response.content[0].text if response.content else "",
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """发送流式聊天请求到Anthropic"""
        client = self._get_client()
        
        # 分离system消息
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        async with client.messages.stream(
            model=self.config.model,
            system=system_message,
            messages=chat_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return f"anthropic:{self.config.model}"
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return bool(self.config.api_key)
