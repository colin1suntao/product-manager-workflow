"""并行任务协调器"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from pm_workstation.storage.task_dispatcher import Task, TaskDispatcher, TaskStatus, TaskType


class ParallelTaskGroup(BaseModel):
    """并行任务组"""
    group_id: str  # 组ID
    tasks: list[Task] = Field(default_factory=list)  # 任务列表
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    completed_at: Optional[datetime] = None  # 完成时间
    status: str = "running"  # 状态 (running/completed/failed)
    on_complete: Optional[Callable] = None  # 全部完成回调
    
    def add_task(self, task: Task):
        """添加任务"""
        self.tasks.append(task)
    
    def is_complete(self) -> bool:
        """检查是否全部完成"""
        return all(
            task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for task in self.tasks
        )
    
    def is_failed(self) -> bool:
        """检查是否有失败"""
        return any(
            task.status == TaskStatus.FAILED
            for task in self.tasks
        )
    
    def get_results(self) -> dict[str, Any]:
        """获取所有任务结果"""
        results = {}
        for task in self.tasks:
            if task.status == TaskStatus.COMPLETED and task.result:
                results[task.task_type.value] = task.result
        return results


class ParallelCoordinator:
    """并行任务协调器"""
    
    def __init__(self, dispatcher: TaskDispatcher):
        """初始化协调器
        
        Args:
            dispatcher: 任务分发器
        """
        self.dispatcher = dispatcher
        self._groups: dict[str, ParallelTaskGroup] = {}
    
    async def create_parallel_group(
        self,
        group_id: str,
        requirement_data: dict,
        task_types: list[TaskType] = None,
        on_complete: Optional[Callable] = None,
    ) -> ParallelTaskGroup:
        """创建并行任务组
        
        Args:
            group_id: 组ID
            requirement_data: 需求数据
            task_types: 任务类型列表
            on_complete: 全部完成回调
            
        Returns:
            任务组
        """
        if task_types is None:
            task_types = [TaskType.PROTOTYPE, TaskType.DOCUMENTATION]
        
        group = ParallelTaskGroup(
            group_id=group_id,
            on_complete=on_complete,
        )
        
        # 创建并行任务
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
        timeout: Optional[float] = None,
    ) -> ParallelTaskGroup:
        """等待任务组完成
        
        Args:
            group_id: 组ID
            timeout: 超时时间（秒）
            
        Returns:
            任务组
            
        Raises:
            TimeoutError: 超时
        """
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
            
            await asyncio.sleep(0.1)  # 短暂等待
        
        # 更新状态
        if group.is_failed():
            group.status = "failed"
        else:
            group.status = "completed"
        
        group.completed_at = datetime.utcnow()
        
        # 触发完成回调
        if group.on_complete:
            await group.on_complete(group)
        
        return group
    
    def get_group(self, group_id: str) -> Optional[ParallelTaskGroup]:
        """获取任务组
        
        Args:
            group_id: 组ID
            
        Returns:
            任务组
        """
        return self._groups.get(group_id)
    
    def get_all_groups(self) -> list[ParallelTaskGroup]:
        """获取所有任务组"""
        return list(self._groups.values())
    
    def clear_groups(self):
        """清除所有任务组"""
        self._groups.clear()
