"""任务分发器"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from pm_workstation.models.core import StructuredRequirement
from pm_workstation.storage.message_queue import MessageQueue


class TaskType(str, Enum):
    """任务类型"""
    PROTOTYPE = "prototype"  # 原型生成
    DOCUMENTATION = "documentation"  # 文档生成
    VERIFICATION = "verification"  # 校验


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """任务"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    data: dict = Field(default_factory=dict)  # 任务数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None
    
    def start(self):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete(self, result: dict):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result
    
    def fail(self, error_message: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message


class TaskDispatcher:
    """任务分发器 - 分发任务到Agent"""
    
    def __init__(
        self,
        message_queue: MessageQueue,
        channels: Optional[dict[TaskType, str]] = None,
    ):
        """初始化任务分发器
        
        Args:
            message_queue: 消息队列
            channels: 任务类型到频道的映射
        """
        self.message_queue = message_queue
        self.channels = channels or {
            TaskType.PROTOTYPE: "tasks:prototype",
            TaskType.DOCUMENTATION: "tasks:documentation",
            TaskType.VERIFICATION: "tasks:verification",
        }
        self._handlers: dict[TaskType, Callable] = {}
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        """注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数 (async function)
        """
        self._handlers[task_type] = handler
    
    async def dispatch(
        self,
        task_type: TaskType,
        data: dict,
        callback: Optional[Callable] = None,
    ) -> Task:
        """分发任务
        
        Args:
            task_type: 任务类型
            data: 任务数据
            callback: 完成回调
            
        Returns:
            任务对象
        """
        task = Task(
            task_type=task_type,
            data=data,
        )
        
        # 发布任务到频道
        channel = self.channels.get(task_type)
        if not channel:
            raise ValueError(f"Unknown task type: {task_type}")
        
        await self.message_queue.publish(channel, task.model_dump())
        
        # 如果有本地处理器，立即执行
        if task_type in self._handlers:
            task.start()
            try:
                handler = self._handlers[task_type]
                result = await handler(data)
                task.complete(result)
                
                if callback:
                    await callback(task)
            except Exception as e:
                task.fail(str(e))
        
        return task
    
    async def dispatch_parallel(
        self,
        requirement: Any,  # StructuredRequirement or dict
        callbacks: Optional[dict[TaskType, Callable]] = None,
    ) -> list[Task]:
        """并行分发任务
        
        Args:
            requirement: 结构化需求或字典
            callbacks: 任务完成回调
            
        Returns:
            任务列表
        """
        import asyncio
        
        # 支持 StructuredRequirement 或 dict
        if hasattr(requirement, 'model_dump'):
            tasks_data = requirement.model_dump()
        else:
            tasks_data = requirement
        
        coroutines = []
        
        # 原型生成任务
        proto_callback = callbacks.get(TaskType.PROTOTYPE) if callbacks else None
        coroutines.append(
            self.dispatch(TaskType.PROTOTYPE, tasks_data, proto_callback)
        )
        
        # 文档生成任务
        doc_callback = callbacks.get(TaskType.DOCUMENTATION) if callbacks else None
        coroutines.append(
            self.dispatch(TaskType.DOCUMENTATION, tasks_data, doc_callback)
        )
        
        # 并行执行
        tasks = await asyncio.gather(*coroutines)
        
        return list(tasks)
    
    async def dispatch_verification(
        self,
        prototype_result: dict,
        document_result: dict,
        callback: Optional[Callable] = None,
    ) -> Task:
        """分发校验任务
        
        Args:
            prototype_result: 原型生成结果
            document_result: 文档生成结果
            callback: 完成回调
            
        Returns:
            任务对象
        """
        data = {
            "prototype": prototype_result,
            "document": document_result,
        }
        
        return await self.dispatch(
            TaskType.VERIFICATION,
            data,
            callback,
        )
    
    def get_channel(self, task_type: TaskType) -> str:
        """获取任务频道
        
        Args:
            task_type: 任务类型
            
        Returns:
            频道名称
        """
        return self.channels.get(task_type, f"tasks:{task_type.value}")
