"""LLM抽象基类"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel


class LLMMessage(BaseModel):
    """LLM消息"""
    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    """LLM响应"""
    content: str
    model: str
    usage: Optional[dict[str, int]] = None  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    api_key: str = ""
    base_url: Optional[str] = None


class LLMBackend(ABC):
    """LLM后端抽象基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """发送聊天请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            LLM响应
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ):
        """发送流式聊天请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Yields:
            LLM响应片段
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查模型是否可用"""
        pass
