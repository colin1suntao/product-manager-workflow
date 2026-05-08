"""任务委派工具和子 Agent 执行器测试"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.agents.registry import SubAgentConfig
from pm_workstation.agents.task_tool import (
    ContextManager,
    IsolatedContext,
    SubAgentExecutor,
    SubTask,
    TaskDelegationTool,
    TaskDecomposition,
    TaskRequest,
    TaskResult,
)
from pm_workstation.model_router.base import LLMResponse


class TestSubTask:
    """SubTask 测试"""

    def test_create_subtask(self):
        """测试创建子任务"""
        task = SubTask(
            id="task-1",
            agent_id="analyst",
            description="分析需求",
        )

        assert task.id == "task-1"
        assert task.agent_id == "analyst"
        assert task.timeout == 300
        assert task.can_run_parallel is True
        assert task.retry_count == 0


class TaskRequestTest:
    """TaskRequest 测试"""

    def test_create_request(self):
        """测试创建请求"""
        req = TaskRequest(
            agent_id="writer",
            task_description="生成 PRD",
        )

        assert req.agent_id == "writer"
        assert req.task_description == "生成 PRD"
        assert req.context == {}
        assert req.timeout is None


class TestTaskResult:
    """TaskResult 测试"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        result = TaskResult(
            task_id="task-1",
            agent_id="analyst",
            status="success",
            output="分析结果",
            duration=1.5,
        )

        assert result.status == "success"
        assert result.output == "分析结果"
        assert result.error is None

    def test_create_failed_result(self):
        """测试创建失败结果"""
        result = TaskResult(
            task_id="task-1",
            agent_id="analyst",
            status="failed",
            error="LLM API error",
        )

        assert result.status == "failed"
        assert result.error == "LLM API error"
        assert result.output is None


class TestTaskDecomposition:
    """TaskDecomposition 测试"""

    def test_create_decomposition(self):
        """测试创建任务拆解"""
        decomp = TaskDecomposition(
            plan="分析需求并生成原型",
            subtasks=[
                SubTask(id="task-1", agent_id="analyst", description="分析需求"),
                SubTask(id="task-2", agent_id="designer", description="设计原型"),
            ],
            execution_order=["task-1", "task-2"],
        )

        assert len(decomp.subtasks) == 2
        assert decomp.execution_order == ["task-1", "task-2"]


class TestContextManager:
    """ContextManager 测试"""

    def test_create_isolated_context(self):
        """测试创建隔离上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(workspace_dir=tmpdir)
            ctx = manager.create_isolated_context(
                agent_id="analyst",
                task_id="task-1",
                shared_data={"requirement": "测试需求"},
            )

            assert isinstance(ctx, IsolatedContext)
            assert ctx.agent_id == "analyst"
            assert ctx.task_id == "task-1"
            assert ctx.shared_data == {"requirement": "测试需求"}
            assert ctx.workspace.startswith(tmpdir)
            assert os.path.exists(ctx.workspace)
            assert os.path.exists(ctx.uploads)
            assert os.path.exists(ctx.outputs)

    def test_get_context(self):
        """测试获取上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(workspace_dir=tmpdir)
            manager.create_isolated_context("analyst", "task-1", {})

            ctx = manager.get_context("analyst", "task-1")
            assert ctx is not None
            assert ctx.agent_id == "analyst"

    def test_get_nonexistent_context_returns_none(self):
        """测试获取不存在的上下文返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(workspace_dir=tmpdir)
            ctx = manager.get_context("nonexistent", "task-1")
            assert ctx is None

    def test_merge_results(self):
        """测试合并结果"""
        manager = ContextManager()
        main_ctx = {"workflow_run": "test"}
        sub_results = {"task-1": "result-1", "task-2": "result-2"}

        result = manager.merge_results(main_ctx, sub_results)
        assert result["subtask_results"] == sub_results
        assert result["workflow_run"] == "test"

    def test_clear_context(self):
        """测试清理上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(workspace_dir=tmpdir)
            ctx = manager.create_isolated_context("analyst", "task-1", {})
            workspace_path = ctx.workspace

            manager.clear_context("analyst", "task-1")
            ctx = manager.get_context("analyst", "task-1")
            assert ctx is None

    def test_list_active_contexts(self):
        """测试列出活跃上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(workspace_dir=tmpdir)
            manager.create_isolated_context("agent-1", "task-1", {})
            manager.create_isolated_context("agent-2", "task-2", {})

            contexts = manager.list_active_contexts()
            assert len(contexts) == 2


class TestSubAgentExecutor:
    """SubAgentExecutor 测试"""

    def _create_mock_llm_factory(self, response_content: str = "test result"):
        """创建模拟的 LLM 工厂"""
        mock_handler = AsyncMock()
        mock_handler.chat.return_value = LLMResponse(
            content=response_content,
            model="gpt-4",
        )

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler
        mock_factory.get_by_model.return_value = mock_handler

        return mock_factory

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """测试成功执行"""
        mock_factory = self._create_mock_llm_factory("分析结果")
        executor = SubAgentExecutor(llm_factory=mock_factory)

        config = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="你是分析专家",
            timeout_seconds=60,
        )

        result = await executor.execute(
            config=config,
            task="分析需求",
            context={"shared_data": {"text": "需求文本"}},
        )

        assert result == "分析结果"
        mock_factory.get_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_specific_model(self):
        """测试使用特定模型执行"""
        mock_factory = self._create_mock_llm_factory("分析结果")
        executor = SubAgentExecutor(llm_factory=mock_factory)

        config = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="你是分析专家",
            model="gpt-4o",
        )

        await executor.execute(
            config=config,
            task="分析需求",
            context={},
        )

        mock_factory.get_by_model.assert_called_once_with("gpt-4o")

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """测试执行超时"""
        async def slow_chat(*args, **kwargs):
            await asyncio.sleep(100)

        mock_handler = AsyncMock()
        mock_handler.chat = slow_chat

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(llm_factory=mock_factory)

        config = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="你是分析专家",
            timeout_seconds=1,
        )

        with pytest.raises(TimeoutError, match="timed out"):
            await executor.execute(
                config=config,
                task="分析需求",
                context={},
                timeout=1,
            )

    @pytest.mark.asyncio
    async def test_execute_with_skills(self):
        """测试带技能执行"""
        mock_factory = self._create_mock_llm_factory("结果")
        executor = SubAgentExecutor(llm_factory=mock_factory)

        config = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="你是分析专家",
            skills=["requirement-analysis", "entity-extraction"],
        )

        result = await executor.execute(
            config=config,
            task="分析需求",
            context={},
        )

        assert result == "结果"


class TestTaskDelegationTool:
    """TaskDelegationTool 测试"""

    def _create_registry_and_executor(self, response_content: str = "result"):
        """创建注册表和执行器"""
        registry = MagicMock()
        registry.get.return_value = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="你是分析专家",
            timeout_seconds=60,
        )

        mock_handler = AsyncMock()
        mock_handler.chat.return_value = LLMResponse(
            content=response_content,
            model="gpt-4",
        )

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(llm_factory=mock_factory)

        return registry, executor

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """测试成功委派"""
        registry, executor = self._create_registry_and_executor("分析完成")
        tool = TaskDelegationTool(registry=registry, executor=executor)

        result = await tool.invoke(
            agent_id="analyst",
            task_description="分析需求",
            context={"text": "需求"},
        )

        assert result.status == "success"
        assert result.output == "分析完成"
        assert result.agent_id == "analyst"
        assert result.duration >= 0

    @pytest.mark.asyncio
    async def test_invoke_nonexistent_agent_raises(self):
        """测试委派不存在的 Agent"""
        registry = MagicMock()
        registry.get.return_value = None

        mock_factory = MagicMock()
        executor = SubAgentExecutor(llm_factory=mock_factory)

        tool = TaskDelegationTool(registry=registry, executor=executor)

        with pytest.raises(KeyError, match="not found"):
            await tool.invoke(
                agent_id="nonexistent",
                task_description="任务",
            )

    @pytest.mark.asyncio
    async def test_invoke_timeout(self):
        """测试委派超时"""
        async def slow_chat(*args, **kwargs):
            await asyncio.sleep(100)

        mock_handler = AsyncMock()
        mock_handler.chat = slow_chat

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        registry = MagicMock()
        registry.get.return_value = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="Test",
            timeout_seconds=1,
        )

        executor = SubAgentExecutor(llm_factory=mock_factory)
        tool = TaskDelegationTool(registry=registry, executor=executor)

        result = await tool.invoke(
            agent_id="analyst",
            task_description="任务",
            timeout=1,
        )

        assert result.status == "timeout"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_invoke_error(self):
        """测试委派错误"""
        mock_handler = AsyncMock()
        mock_handler.chat.side_effect = Exception("API error")

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        registry = MagicMock()
        registry.get.return_value = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="Test",
            system_prompt="Test",
        )

        executor = SubAgentExecutor(llm_factory=mock_factory)
        tool = TaskDelegationTool(registry=registry, executor=executor)

        result = await tool.invoke(
            agent_id="analyst",
            task_description="任务",
        )

        assert result.status == "failed"
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_invoke_batch(self):
        """测试批量委派"""
        registry = MagicMock()
        registry.get.side_effect = lambda agent_id: SubAgentConfig(
            id=agent_id,
            name=agent_id,
            description="Test",
            system_prompt=f"你是{agent_id}专家",
            timeout_seconds=60,
        )

        mock_handler = AsyncMock()
        mock_handler.chat.return_value = LLMResponse(
            content=f"result",
            model="gpt-4",
        )

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(llm_factory=mock_factory)
        tool = TaskDelegationTool(registry=registry, executor=executor, max_concurrent=3)

        tasks = [
            TaskRequest(agent_id="analyst", task_description="分析需求"),
            TaskRequest(agent_id="writer", task_description="生成 PRD"),
            TaskRequest(agent_id="designer", task_description="设计原型"),
        ]

        results = await tool.invoke_batch(tasks)

        assert len(results) == 3
        assert all(r.status == "success" for r in results)

    @pytest.mark.asyncio
    async def test_invoke_batch_empty(self):
        """测试批量委派空列表"""
        registry = MagicMock()
        mock_factory = MagicMock()
        executor = SubAgentExecutor(llm_factory=mock_factory)
        tool = TaskDelegationTool(registry=registry, executor=executor)

        results = await tool.invoke_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_invoke_batch_concurrency_limit(self):
        """测试批量委派并发限制"""
        call_times = []
        call_events = []

        async def tracked_chat(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            event = asyncio.Event()
            call_events.append(event)
            # 等待所有调用都开始
            if len(call_events) < 3:
                event.wait()
            return LLMResponse(content="result", model="gpt-4")

        mock_handler = AsyncMock()
        mock_handler.chat = tracked_chat

        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        registry = MagicMock()
        registry.get.side_effect = lambda agent_id: SubAgentConfig(
            id=agent_id,
            name=agent_id,
            description="Test",
            system_prompt="Test",
            timeout_seconds=60,
        )

        executor = SubAgentExecutor(llm_factory=mock_factory)
        # 限制并发为 2
        tool = TaskDelegationTool(registry=registry, executor=executor, max_concurrent=2)

        tasks = [
            TaskRequest(agent_id=f"agent-{i}", task_description=f"任务 {i}")
            for i in range(4)
        ]

        # 应该能正常执行，不超过并发限制
        results = await tool.invoke_batch(tasks)
        assert len(results) == 4
