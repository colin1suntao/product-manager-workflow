"""降级处理器"""

import asyncio
from typing import Any

from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse


class FallbackHandler:
    """降级处理器 - 模型失败时切换备选模型"""

    def __init__(
        self,
        primary_model: LLMBackend,
        fallback_models: list[LLMBackend],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """初始化降级处理器

        Args:
            primary_model: 主模型
            fallback_models: 备选模型列表
            max_retries: 最大重试次数
            base_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
        """
        self.primary_model = primary_model
        self.fallback_models = fallback_models
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_model = primary_model

    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """发送聊天请求，支持降级和重试

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLM响应

        Raises:
            Exception: 所有模型都失败时抛出
        """
        # 尝试所有模型
        all_models = [self.primary_model] + self.fallback_models

        for model in all_models:
            self.current_model = model
            last_error = None

            for attempt in range(self.max_retries):
                try:
                    return await model.chat(messages, **kwargs)
                except Exception as e:
                    last_error = e

                    if attempt < self.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        await asyncio.sleep(delay)

            # 当前模型失败，切换到下一个
            continue

        # 所有模型都失败
        raise Exception(
            f"All models failed. Last error: {last_error}"
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ):
        """发送流式聊天请求，支持降级

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            LLM响应片段
        """
        all_models = [self.primary_model] + self.fallback_models

        for model in all_models:
            self.current_model = model
            try:
                async for chunk in model.chat_stream(messages, **kwargs):
                    yield chunk
                return  # 成功完成
            except Exception:
                continue

        # 所有模型都失败
        raise Exception("All models failed for streaming")

    def _calculate_delay(self, attempt: int) -> float:
        """计算指数退避延迟

        Args:
            attempt: 重试次数

        Returns:
            延迟时间（秒）
        """
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)

    def get_current_model(self) -> LLMBackend:
        """获取当前使用的模型"""
        return self.current_model

    def is_using_fallback(self) -> bool:
        """检查是否在使用备选模型"""
        return self.current_model is not self.primary_model
