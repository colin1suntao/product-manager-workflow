"""中间件链模块

实现可组合的中间件链，处理横切关注点如上下文管理、错误处理、摘要压缩等。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from pm_workstation.agents.registry import SubAgentConfig

logger = logging.getLogger(__name__)


class MiddlewareState(BaseModel):
    """中间件状态"""

    agent_id: str = ""
    task_id: str = ""
    config: SubAgentConfig | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Middleware(ABC):
    """中间件抽象基类

    每个中间件可以在 Agent 执行前后插入自定义逻辑。
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @abstractmethod
    async def before_agent(
        self,
        state: MiddlewareState,
    ) -> MiddlewareState:
        """在 Agent 执行前调用

        Args:
            state: 中间件状态

        Returns:
            更新后的状态
        """
        pass

    @abstractmethod
    async def after_agent(
        self,
        state: MiddlewareState,
    ) -> MiddlewareState:
        """在 Agent 执行后调用

        Args:
            state: 中间件状态

        Returns:
            更新后的状态
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled})"


class MiddlewareChain:
    """中间件链

    按顺序执行所有注册的中间件。
    """

    def __init__(self, middlewares: list[Middleware] | None = None):
        self._middlewares: list[Middleware] = middlewares or []

    def add(self, middleware: Middleware) -> None:
        """添加中间件

        Args:
            middleware: 中间件实例
        """
        self._middlewares.append(middleware)

    def remove(self, middleware_class: type[Middleware]) -> None:
        """移除指定类型的中间件

        Args:
            middleware_class: 中间件类
        """
        self._middlewares = [
            m for m in self._middlewares
            if not isinstance(m, middleware_class)
        ]

    async def execute_before(
        self,
        state: MiddlewareState,
    ) -> MiddlewareState:
        """执行所有中间件的 before_agent 方法

        Args:
            state: 中间件状态

        Returns:
            更新后的状态
        """
        for middleware in self._middlewares:
            if not middleware.enabled:
                continue
            try:
                state = await middleware.before_agent(state)
            except Exception as e:
                logger.error(
                    f"Middleware {middleware.__class__.__name__} before_agent failed: {e}"
                )
                state.error = str(e)
        return state

    async def execute_after(
        self,
        state: MiddlewareState,
    ) -> MiddlewareState:
        """执行所有中间件的 after_agent 方法

        Args:
            state: 中间件状态

        Returns:
            更新后的状态
        """
        for middleware in reversed(self._middlewares):
            if not middleware.enabled:
                continue
            try:
                state = await middleware.after_agent(state)
            except Exception as e:
                logger.error(
                    f"Middleware {middleware.__class__.__name__} after_agent failed: {e}"
                )
                if not state.error:
                    state.error = str(e)
        return state

    async def execute(
        self,
        state: MiddlewareState,
        agent_func: callable,
    ) -> MiddlewareState:
        """完整执行流程：before -> agent_func -> after

        Args:
            state: 中间件状态
            agent_func: Agent 执行函数

        Returns:
            更新后的状态
        """
        # 执行 before
        state = await self.execute_before(state)
        if state.error:
            return state

        # 执行 Agent 函数
        try:
            result = await agent_func()
            state.output_data["result"] = result
        except Exception as e:
            state.error = str(e)

        # 执行 after
        state = await self.execute_after(state)
        return state

    def list_middlewares(self) -> list[str]:
        """列出所有中间件

        Returns:
            中间件名称列表
        """
        return [m.__class__.__name__ for m in self._middlewares]

    def __len__(self) -> int:
        return len(self._middlewares)
