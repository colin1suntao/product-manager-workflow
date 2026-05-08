"""审计日志中间件

记录 Agent 执行的审计信息，包括执行时间、状态、错误等。
"""

import logging
import time

from pm_workstation.agents.middlewares.base import Middleware, MiddlewareState

logger = logging.getLogger(__name__)


class AuditMiddleware(Middleware):
    """审计日志中间件

    记录 Agent 执行的审计信息。
    """

    def __init__(self, enabled: bool = True):
        super().__init__(enabled=enabled)
        self._start_times: dict[str, float] = {}

    async def before_agent(self, state: MiddlewareState) -> MiddlewareState:
        """记录执行开始时间"""
        task_key = f"{state.agent_id}:{state.task_id}"
        self._start_times[task_key] = time.monotonic()

        logger.info(
            f"[AUDIT] Agent '{state.agent_id}' starting task '{state.task_id}'"
        )

        return state

    async def after_agent(self, state: MiddlewareState) -> MiddlewareState:
        """记录执行结果"""
        task_key = f"{state.agent_id}:{state.task_id}"
        start_time = self._start_times.pop(task_key, 0)
        duration = time.monotonic() - start_time

        status = "failed" if state.error else "success"

        audit_info = {
            "agent_id": state.agent_id,
            "task_id": state.task_id,
            "status": status,
            "duration": round(duration, 3),
            "error": state.error,
        }

        # 记录到 metadata
        state.metadata["audit"] = audit_info

        # 记录日志
        if state.error:
            logger.warning(
                f"[AUDIT] Agent '{state.agent_id}' task '{state.task_id}' "
                f"FAILED after {duration:.3f}s: {state.error}"
            )
        else:
            logger.info(
                f"[AUDIT] Agent '{state.agent_id}' task '{state.task_id}' "
                f"SUCCEEDED in {duration:.3f}s"
            )

        return state
