"""状态持久化中间件

在 Agent 执行后将状态保存到持久化存储。
"""

import json
import logging
import os
from pathlib import Path

from pm_workstation.agents.middlewares.base import Middleware, MiddlewareState

logger = logging.getLogger(__name__)


class StatePersistenceMiddleware(Middleware):
    """状态持久化中间件

    在 Agent 执行后将状态保存到文件系统。
    """

    def __init__(
        self,
        persistence_dir: str | None = None,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.persistence_dir = persistence_dir or os.path.join(
            os.path.expanduser("~"),
            ".pm_workstation",
            "state_persistence",
        )
        os.makedirs(self.persistence_dir, exist_ok=True)

    async def before_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行前尝试加载已保存的状态"""
        state_file = self._get_state_file(state.agent_id, state.task_id)
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    saved_state = json.load(f)
                # 合并保存的状态
                state.metadata.update(saved_state.get("metadata", {}))
                logger.debug(f"Loaded saved state for {state.agent_id}:{state.task_id}")
            except Exception as e:
                logger.warning(f"Failed to load saved state: {e}")

        return state

    async def after_agent(self, state: MiddlewareState) -> MiddlewareState:
        """执行后保存状态"""
        if not state.agent_id or not state.task_id:
            return state

        state_file = self._get_state_file(state.agent_id, state.task_id)

        try:
            state_data = {
                "agent_id": state.agent_id,
                "task_id": state.task_id,
                "error": state.error,
                "metadata": state.metadata,
                "output_keys": list(state.output_data.keys()),
            }

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved state for {state.agent_id}:{state.task_id}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

        return state

    def _get_state_file(self, agent_id: str, task_id: str) -> Path:
        """获取状态文件路径"""
        safe_agent_id = agent_id.replace("/", "_").replace(" ", "_")
        safe_task_id = task_id.replace("/", "_").replace(" ", "_")
        return Path(self.persistence_dir) / f"{safe_agent_id}_{safe_task_id}.json"

    def clear_state(self, agent_id: str, task_id: str) -> None:
        """清理状态文件"""
        state_file = self._get_state_file(agent_id, task_id)
        if state_file.exists():
            state_file.unlink()
