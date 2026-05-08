"""上下文管理中间件

在 Agent 执行前创建隔离上下文，执行后清理。
"""


from pm_workstation.agents.middlewares.base import Middleware, MiddlewareState
from pm_workstation.agents.task_tool import ContextManager


class ContextMiddleware(Middleware):
    """上下文管理中间件

    负责在 Agent 执行前创建隔离上下文，执行后合并结果。
    """

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.context_manager = context_manager or ContextManager()

    async def before_agent(self, state: MiddlewareState) -> MiddlewareState:
        """创建隔离上下文"""
        if not state.agent_id or not state.task_id:
            return state

        # 创建隔离上下文
        isolated_ctx = self.context_manager.create_isolated_context(
            agent_id=state.agent_id,
            task_id=state.task_id,
            shared_data=state.input_data,
        )

        # 将上下文信息存储到 metadata
        state.metadata["context_workspace"] = isolated_ctx.workspace
        state.metadata["context_uploads"] = isolated_ctx.uploads
        state.metadata["context_outputs"] = isolated_ctx.outputs

        return state

    async def after_agent(self, state: MiddlewareState) -> MiddlewareState:
        """清理上下文"""
        if not state.agent_id or not state.task_id:
            return state

        # 清理隔离上下文
        self.context_manager.clear_context(state.agent_id, state.task_id)

        return state
