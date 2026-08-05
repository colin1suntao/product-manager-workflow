"""并行任务协调器"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from pm_workstation.storage.task_dispatcher import Task, TaskDispatcher, TaskStatus, TaskType


class ParallelTaskGroup(BaseModel):
    """并行任务组"""
    group_id: str
    tasks: list[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str = "running"
    on_complete: Callable | None = None

    def add_task(self, task: Task):
        self.tasks.append(task)

    def is_complete(self) -> bool:
        return all(
            task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for task in self.tasks
        )

    def is_failed(self) -> bool:
        return any(task.status == TaskStatus.FAILED for task in self.tasks)

    def get_results(self) -> dict[str, Any]:
        results = {}
        for task in self.tasks:
            if task.status == TaskStatus.COMPLETED and task.result:
                results[task.task_type.value] = task.result
        return results


class ParallelCoordinator:
    """并行任务协调器"""

    def __init__(self, dispatcher: TaskDispatcher):
        self.dispatcher = dispatcher
        self._groups: dict[str, ParallelTaskGroup] = {}

    async def create_parallel_group(
        self,
        group_id: str,
        requirement_data: dict,
        task_types: list[TaskType] = None,
        on_complete: Callable | None = None,
    ) -> ParallelTaskGroup:
        if task_types is None:
            task_types = [TaskType.PROTOTYPE, TaskType.DOCUMENTATION]

        group = ParallelTaskGroup(
            group_id=group_id,
            on_complete=on_complete,
        )

        tasks = await self.dispatcher.dispatch_parallel(
            requirement_data,
            callbacks=None,
        )

        for task in tasks:
            group.add_task(task)

        self._groups[group_id] = group

        return group

    async def wait_for_completion(
        self,
        group_id: str,
        timeout: float | None = None,
    ) -> ParallelTaskGroup:
        group = self._groups.get(group_id)
        if not group:
            raise ValueError(f"Group not found: {group_id}")

        start_time = datetime.utcnow()

        while not group.is_complete():
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    group.status = "failed"
                    raise TimeoutError(f"Group {group_id} timed out after {timeout}s")

            await asyncio.sleep(0.5)

        if group.is_failed():
            group.status = "failed"
        else:
            group.status = "completed"

        group.completed_at = datetime.utcnow()

        if group.on_complete:
            await group.on_complete(group)

        return group

    def get_group(self, group_id: str) -> ParallelTaskGroup | None:
        return self._groups.get(group_id)

    def get_all_groups(self) -> list[ParallelTaskGroup]:
        return list(self._groups.values())

    def clear_groups(self):
        self._groups.clear()
