"""任务分发测试"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.storage.message_queue import MessageQueue
from pm_workstation.storage.parallel_coordinator import ParallelCoordinator, ParallelTaskGroup
from pm_workstation.storage.task_dispatcher import Task, TaskDispatcher, TaskStatus, TaskType


class TestTask:
    """Task测试"""
    
    def test_create_task(self):
        """测试创建任务"""
        task = Task(
            task_type=TaskType.PROTOTYPE,
            data={"requirement": "test"},
        )
        
        assert task.task_type == TaskType.PROTOTYPE
        assert task.status == TaskStatus.PENDING
        assert task.id is not None
    
    def test_start_task(self):
        """测试开始任务"""
        task = Task(task_type=TaskType.PROTOTYPE)
        task.start()
        
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
    
    def test_complete_task(self):
        """测试完成任务"""
        task = Task(task_type=TaskType.PROTOTYPE)
        task.start()
        task.complete({"result": "success"})
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == {"result": "success"}
    
    def test_fail_task(self):
        """测试任务失败"""
        task = Task(task_type=TaskType.PROTOTYPE)
        task.start()
        task.fail("error message")
        
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "error message"


class TestTaskDispatcher:
    """TaskDispatcher测试"""
    
    @pytest.mark.asyncio
    async def test_dispatch_task(self):
        """测试分发任务"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        task = await dispatcher.dispatch(
            task_type=TaskType.PROTOTYPE,
            data={"requirement": "test"},
        )
        
        assert task.task_type == TaskType.PROTOTYPE
        assert task.status == TaskStatus.PENDING
        mock_mq.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_with_handler(self):
        """测试分发带处理器的任务"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        # 注册处理器
        async def mock_handler(data):
            return {"processed": True}
        
        dispatcher.register_handler(TaskType.PROTOTYPE, mock_handler)
        
        task = await dispatcher.dispatch(
            task_type=TaskType.PROTOTYPE,
            data={"requirement": "test"},
        )
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"processed": True}
    
    @pytest.mark.asyncio
    async def test_dispatch_with_callback(self):
        """测试分发带回调的任务"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        callback = AsyncMock()
        
        async def mock_handler(data):
            return {"result": "ok"}
        
        dispatcher.register_handler(TaskType.PROTOTYPE, mock_handler)
        
        task = await dispatcher.dispatch(
            task_type=TaskType.PROTOTYPE,
            data={"requirement": "test"},
            callback=callback,
        )
        
        callback.assert_called_once_with(task)
    
    @pytest.mark.asyncio
    async def test_dispatch_handler_failure(self):
        """测试处理器失败"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        async def failing_handler(data):
            raise Exception("Handler error")
        
        dispatcher.register_handler(TaskType.PROTOTYPE, failing_handler)
        
        task = await dispatcher.dispatch(
            task_type=TaskType.PROTOTYPE,
            data={"requirement": "test"},
        )
        
        assert task.status == TaskStatus.FAILED
        assert "Handler error" in task.error_message
    
    @pytest.mark.asyncio
    async def test_dispatch_parallel(self):
        """测试并行分发"""
        from pm_workstation.models.core import RuleTreeNode, StructuredRequirement
        
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="test")
        )
        
        tasks = await dispatcher.dispatch_parallel(requirement)
        
        assert len(tasks) == 2  # prototype + documentation
        assert any(t.task_type == TaskType.PROTOTYPE for t in tasks)
        assert any(t.task_type == TaskType.DOCUMENTATION for t in tasks)
    
    @pytest.mark.asyncio
    async def test_dispatch_verification(self):
        """测试分发校验任务"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        task = await dispatcher.dispatch_verification(
            prototype_result={"url": "proto"},
            document_result={"url": "doc"},
        )
        
        assert task.task_type == TaskType.VERIFICATION
        assert task.data["prototype"]["url"] == "proto"
    
    def test_get_channel(self):
        """测试获取频道"""
        mock_mq = MagicMock(spec=MessageQueue)
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        assert dispatcher.get_channel(TaskType.PROTOTYPE) == "tasks:prototype"
        assert dispatcher.get_channel(TaskType.DOCUMENTATION) == "tasks:documentation"
    
    def test_custom_channels(self):
        """测试自定义频道"""
        mock_mq = MagicMock(spec=MessageQueue)
        custom_channels = {
            TaskType.PROTOTYPE: "custom:proto",
        }
        dispatcher = TaskDispatcher(
            message_queue=mock_mq,
            channels=custom_channels,
        )
        
        assert dispatcher.get_channel(TaskType.PROTOTYPE) == "custom:proto"
        # 默认频道仍然可用
        assert dispatcher.get_channel(TaskType.DOCUMENTATION) == "tasks:documentation"


class TestParallelTaskGroup:
    """ParallelTaskGroup测试"""
    
    def test_create_group(self):
        """测试创建任务组"""
        group = ParallelTaskGroup(group_id="group-001")
        
        assert group.group_id == "group-001"
        assert group.tasks == []
        assert group.status == "running"
    
    def test_add_task(self):
        """测试添加任务"""
        group = ParallelTaskGroup(group_id="group-001")
        
        task1 = Task(task_type=TaskType.PROTOTYPE)
        task2 = Task(task_type=TaskType.DOCUMENTATION)
        
        group.add_task(task1)
        group.add_task(task2)
        
        assert len(group.tasks) == 2
    
    def test_is_complete_all_completed(self):
        """测试全部完成"""
        group = ParallelTaskGroup(group_id="group-001")
        
        task1 = Task(task_type=TaskType.PROTOTYPE)
        task1.complete({"result": "ok"})
        
        task2 = Task(task_type=TaskType.DOCUMENTATION)
        task2.complete({"result": "ok"})
        
        group.add_task(task1)
        group.add_task(task2)
        
        assert group.is_complete() is True
    
    def test_is_complete_partial(self):
        """测试部分完成"""
        group = ParallelTaskGroup(group_id="group-001")
        
        task1 = Task(task_type=TaskType.PROTOTYPE)
        task1.complete({"result": "ok"})
        
        task2 = Task(task_type=TaskType.DOCUMENTATION)
        # task2 仍然是 pending
        
        group.add_task(task1)
        group.add_task(task2)
        
        assert group.is_complete() is False
    
    def test_is_failed(self):
        """测试失败检测"""
        group = ParallelTaskGroup(group_id="group-001")
        
        task1 = Task(task_type=TaskType.PROTOTYPE)
        task1.complete({"result": "ok"})
        
        task2 = Task(task_type=TaskType.DOCUMENTATION)
        task2.fail("error")
        
        group.add_task(task1)
        group.add_task(task2)
        
        assert group.is_failed() is True
    
    def test_get_results(self):
        """测试获取结果"""
        group = ParallelTaskGroup(group_id="group-001")
        
        task1 = Task(task_type=TaskType.PROTOTYPE)
        task1.complete({"url": "proto.html"})
        
        task2 = Task(task_type=TaskType.DOCUMENTATION)
        task2.complete({"url": "doc.md"})
        
        task3 = Task(task_type=TaskType.VERIFICATION)
        task3.fail("error")  # 失败任务不应该有结果
        
        group.add_task(task1)
        group.add_task(task2)
        group.add_task(task3)
        
        results = group.get_results()
        
        assert "prototype" in results
        assert "documentation" in results
        assert "verification" not in results  # 失败的任务不包含


class TestParallelCoordinator:
    """ParallelCoordinator测试"""
    
    @pytest.mark.asyncio
    async def test_create_parallel_group(self):
        """测试创建并行任务组"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        group = await coordinator.create_parallel_group(
            group_id="group-001",
            requirement_data={"test": "data"},
        )
        
        assert group.group_id == "group-001"
        assert len(group.tasks) == 2
        assert coordinator.get_group("group-001") is group
    
    @pytest.mark.asyncio
    async def test_wait_for_completion(self):
        """测试等待完成"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        group = await coordinator.create_parallel_group(
            group_id="group-001",
            requirement_data={"test": "data"},
        )
        
        # 任务已经通过 dispatcher 的处理器完成（如果没有注册处理器则是 pending）
        # 这里我们模拟手动完成
        for task in group.tasks:
            task.complete({"result": "ok"})
        
        result_group = await coordinator.wait_for_completion("group-001", timeout=1.0)
        
        assert result_group.status == "completed"
        assert result_group.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self):
        """测试等待超时"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        group = await coordinator.create_parallel_group(
            group_id="group-001",
            requirement_data={"test": "data"},
        )
        
        # 任务没有完成，应该超时
        with pytest.raises(TimeoutError):
            await coordinator.wait_for_completion("group-001", timeout=0.1)
        
        assert group.status == "failed"
    
    @pytest.mark.asyncio
    async def test_wait_for_completion_with_callback(self):
        """测试等待完成带回调"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        callback = AsyncMock()
        
        group = await coordinator.create_parallel_group(
            group_id="group-001",
            requirement_data={"test": "data"},
            on_complete=callback,
        )
        
        # 手动完成任务
        for task in group.tasks:
            task.complete({"result": "ok"})
        
        await coordinator.wait_for_completion("group-001")
        
        callback.assert_called_once_with(group)
    
    def test_get_group_not_found(self):
        """测试获取不存在的任务组"""
        mock_mq = MagicMock(spec=MessageQueue)
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        group = coordinator.get_group("nonexistent")
        assert group is None
    
    def test_get_all_groups(self):
        """测试获取所有任务组"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        # 创建多个组需要 await，这里简化测试
        coordinator._groups["group-1"] = ParallelTaskGroup(group_id="group-1")
        coordinator._groups["group-2"] = ParallelTaskGroup(group_id="group-2")
        
        groups = coordinator.get_all_groups()
        assert len(groups) == 2
    
    def test_clear_groups(self):
        """测试清除任务组"""
        mock_mq = MagicMock(spec=MessageQueue)
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        coordinator._groups["group-1"] = ParallelTaskGroup(group_id="group-1")
        coordinator.clear_groups()
        
        assert len(coordinator._groups) == 0


class TestTaskDispatchIntegration:
    """任务分发集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_dispatch_workflow(self):
        """测试完整分发流程"""
        from pm_workstation.models.core import RuleTreeNode, StructuredRequirement
        
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        coordinator = ParallelCoordinator(dispatcher)
        
        # 1. 创建结构化需求
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试规则")
        )
        
        # 2. 并行分发任务
        group = await coordinator.create_parallel_group(
            group_id="workflow-001",
            requirement_data=requirement.model_dump(),
        )
        
        assert len(group.tasks) == 2
        
        # 3. 模拟任务完成
        for task in group.tasks:
            task.complete({"result": f"{task.task_type.value} done"})
        
        # 4. 等待完成
        result = await coordinator.wait_for_completion("workflow-001")
        
        assert result.status == "completed"
        assert result.is_complete() is True
        
        # 5. 获取结果
        results = result.get_results()
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_dispatch_with_custom_handlers(self):
        """测试带自定义处理器的分发"""
        mock_mq = AsyncMock(spec=MessageQueue)
        mock_mq.publish = AsyncMock(return_value=1)
        
        dispatcher = TaskDispatcher(message_queue=mock_mq)
        
        # 注册自定义处理器
        async def proto_handler(data):
            return {"prototype": "generated", "url": "proto.html"}
        
        async def doc_handler(data):
            return {"document": "generated", "url": "doc.md"}
        
        dispatcher.register_handler(TaskType.PROTOTYPE, proto_handler)
        dispatcher.register_handler(TaskType.DOCUMENTATION, doc_handler)
        
        # 并行分发
        from pm_workstation.models.core import RuleTreeNode, StructuredRequirement
        
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试")
        )
        
        tasks = await dispatcher.dispatch_parallel(requirement)
        
        # 验证任务完成
        assert all(t.status == TaskStatus.COMPLETED for t in tasks)
        assert tasks[0].result is not None
        assert tasks[1].result is not None
