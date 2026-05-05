"""集成配置和同步任务存储

提供内存存储实现，用于管理外部系统集成配置和同步任务。
"""

from datetime import datetime
from typing import Optional

from pm_workstation.integrations.models import (
    IntegrationConfig,
    IntegrationType,
    SyncStatus,
    SyncTask,
)


class IntegrationStore:
    """集成配置存储"""

    def __init__(self) -> None:
        self._configs: dict[str, IntegrationConfig] = {}

    def create_config(self, config: IntegrationConfig) -> IntegrationConfig:
        """创建集成配置"""
        self._configs[config.id] = config
        return config

    def get_config(self, config_id: str) -> Optional[IntegrationConfig]:
        """获取集成配置"""
        return self._configs.get(config_id)

    def update_config(self, config_id: str, **kwargs) -> Optional[IntegrationConfig]:
        """更新集成配置"""
        config = self._configs.get(config_id)
        if not config:
            return None

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()
        return config

    def delete_config(self, config_id: str) -> bool:
        """删除集成配置"""
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False

    def list_configs(
        self,
        integration_type: Optional[IntegrationType] = None,
        enabled_only: bool = False,
    ) -> list[IntegrationConfig]:
        """列出集成配置"""
        configs = list(self._configs.values())

        if integration_type:
            configs = [c for c in configs if c.integration_type == integration_type]

        if enabled_only:
            configs = [c for c in configs if c.enabled]

        return configs


class SyncTaskStore:
    """同步任务存储"""

    def __init__(self) -> None:
        self._tasks: dict[str, SyncTask] = {}

    def create_task(self, task: SyncTask) -> SyncTask:
        """创建同步任务"""
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[SyncTask]:
        """获取同步任务"""
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[SyncTask]:
        """更新同步任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        return task

    def list_tasks(
        self,
        integration_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        status: Optional[SyncStatus] = None,
    ) -> list[SyncTask]:
        """列出同步任务"""
        tasks = list(self._tasks.values())

        if integration_id:
            tasks = [t for t in tasks if t.integration_id == integration_id]

        if workflow_id:
            tasks = [t for t in tasks if t.workflow_id == workflow_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """取消同步任务"""
        task = self._tasks.get(task_id)
        if task and task.status in (SyncStatus.PENDING, SyncStatus.RUNNING):
            task.cancel()
            return True
        return False


# 全局存储实例
integration_store = IntegrationStore()
sync_task_store = SyncTaskStore()
