"""摘要压缩中间件

当上下文接近 Token 限制时，压缩上下文并保留关键信息。
"""

import logging

from pm_workstation.agents.middlewares.base import Middleware, MiddlewareState

logger = logging.getLogger(__name__)


class SummarizationMiddleware(Middleware):
    """摘要压缩中间件

    在 Agent 执行后检查输出大小，如果超过阈值则进行压缩。
    """

    def __init__(
        self,
        max_output_length: int = 4000,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.max_output_length = max_output_length

    async def before_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行前不需要操作"""
        return state

    async def after_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行后检查并压缩输出"""
        result = state.output_data.get("result", "")
        if isinstance(result, str) and len(result) > self.max_output_length:
            # 简单截断（实际应该使用 LLM 进行智能摘要）
            truncated = result[: self.max_output_length - 100] + "\n\n[... 内容已截断 ...]"
            state.output_data["result"] = truncated
            state.metadata["summarized"] = True
            state.metadata["original_length"] = len(result)
            state.metadata["compressed_length"] = len(truncated)
            logger.debug(
                f"Output compressed from {len(result)} to {len(truncated)} chars"
            )

        return state
