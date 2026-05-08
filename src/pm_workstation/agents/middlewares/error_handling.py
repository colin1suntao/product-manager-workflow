"""错误处理中间件

捕获 Agent 执行异常，触发重试或降级。
"""

import logging

from pm_workstation.agents.middlewares.base import Middleware, MiddlewareState

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(Middleware):
    """错误处理中间件

    捕获 Agent 执行异常，支持重试和降级策略。
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._retry_counts: dict[str, int] = {}

    async def before_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行前重置重试计数"""
        task_key = f"{state.agent_id}:{state.task_id}"
        if task_key not in self._retry_counts:
            self._retry_counts[task_key] = 0
        return state

    async def after_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行后处理错误"""
        if not state.error:
            # 执行成功，清除重试计数
            task_key = f"{state.agent_id}:{state.task_id}"
            self._retry_counts.pop(task_key, None)
            return state

        task_key = f"{state.agent_id}:{state.task_id}"
        retry_count = self._retry_counts.get(task_key, 0)

        if retry_count < self.max_retries:
            # 记录重试信息
            self._retry_counts[task_key] = retry_count + 1
            state.metadata["retry_count"] = retry_count + 1
            state.metadata["retry_error"] = state.error

            # 指数退避延迟
            delay = self.base_delay * (2 ** retry_count)
            state.metadata["retry_delay"] = delay

            logger.warning(
                f"Agent {state.agent_id} failed (attempt {retry_count + 1}/{self.max_retries}): "
                f"{state.error}. Retrying in {delay}s..."
            )

            # 清除错误标记以便重试
            state.error = None
        else:
            # 超过最大重试次数，保留错误
            state.metadata["max_retries_exceeded"] = True
            logger.error(
                f"Agent {state.agent_id} failed after {self.max_retries} retries: {state.error}"
            )

        return state

    def reset(self) -> None:
        """重置所有重试计数"""
        self._retry_counts.clear()
