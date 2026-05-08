"""中间件链测试"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.agents.middlewares.audit import AuditMiddleware
from pm_workstation.agents.middlewares.base import (
    Middleware,
    MiddlewareChain,
    MiddlewareState,
)
from pm_workstation.agents.middlewares.context import ContextMiddleware
from pm_workstation.agents.middlewares.error_handling import ErrorHandlingMiddleware
from pm_workstation.agents.middlewares.state_persistence import StatePersistenceMiddleware
from pm_workstation.agents.middlewares.summarization import SummarizationMiddleware
from pm_workstation.agents.registry import SubAgentConfig
from pm_workstation.agents.task_tool import ContextManager


class TestMiddlewareBase:
    """Middleware 基类测试"""

    def test_middleware_repr(self):
        """测试中间件字符串表示"""

        class TestMiddleware(Middleware):
            async def before_agent(self, state):
                return state

            async def after_agent(self, state):
                return state

        mw = TestMiddleware(enabled=True)
        assert "TestMiddleware" in repr(mw)
        assert "enabled=True" in repr(mw)


class TestMiddlewareChain:
    """MiddlewareChain 测试"""

    def _create_mock_middleware(
        self,
        before_result: MiddlewareState | None = None,
        after_result: MiddlewareState | None = None,
    ) -> Middleware:
        """创建模拟中间件"""
        mw = MagicMock(spec=Middleware)
        mw.enabled = True
        if before_result:
            mw.before_agent = AsyncMock(return_value=before_result)
        else:
            mw.before_agent = AsyncMock(side_effect=lambda s: s)
        if after_result:
            mw.after_agent = AsyncMock(return_value=after_result)
        else:
            mw.after_agent = AsyncMock(side_effect=lambda s: s)
        return mw

    @pytest.mark.asyncio
    async def test_add_middleware(self):
        """测试添加中间件"""
        chain = MiddlewareChain()
        mw = MagicMock(spec=Middleware)
        mw.enabled = True

        chain.add(mw)
        assert len(chain) == 1

    @pytest.mark.asyncio
    async def test_remove_middleware(self):
        """测试移除中间件"""

        class TestMiddleware(Middleware):
            async def before_agent(self, state):
                return state

            async def after_agent(self, state):
                return state

        chain = MiddlewareChain()
        mw = TestMiddleware()
        chain.add(mw)
        assert len(chain) == 1

        chain.remove(TestMiddleware)
        assert len(chain) == 0

    @pytest.mark.asyncio
    async def test_execute_before(self):
        """测试执行 before_agent"""
        mw = self._create_mock_middleware()
        chain = MiddlewareChain([mw])

        state = MiddlewareState(agent_id="test", task_id="task-1")
        result = await chain.execute_before(state)

        mw.before_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_after(self):
        """测试执行 after_agent"""
        mw = self._create_mock_middleware()
        chain = MiddlewareChain([mw])

        state = MiddlewareState(agent_id="test", task_id="task-1")
        result = await chain.execute_after(state)

        mw.after_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_error_in_before(self):
        """测试 before_agent 错误处理"""
        mw = MagicMock(spec=Middleware)
        mw.enabled = True
        mw.before_agent = AsyncMock(side_effect=Exception("before error"))
        mw.after_agent = AsyncMock(side_effect=lambda s: s)

        chain = MiddlewareChain([mw])
        state = MiddlewareState(agent_id="test", task_id="task-1")
        result = await chain.execute_before(state)

        # 错误应该被捕获
        assert result.error == "before error"

    @pytest.mark.asyncio
    async def test_execute_skips_disabled_middleware(self):
        """测试跳过禁用的中间件"""
        mw = MagicMock(spec=Middleware)
        mw.enabled = False
        mw.before_agent = AsyncMock(side_effect=lambda s: s)
        mw.after_agent = AsyncMock(side_effect=lambda s: s)

        chain = MiddlewareChain([mw])
        state = MiddlewareState(agent_id="test", task_id="task-1")
        await chain.execute_before(state)

        mw.before_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_full_chain(self):
        """测试完整执行流程"""
        mw = self._create_mock_middleware()
        chain = MiddlewareChain([mw])

        async def mock_agent_func():
            return "agent result"

        state = MiddlewareState(agent_id="test", task_id="task-1")
        result = await chain.execute(state, mock_agent_func)

        mw.before_agent.assert_called_once()
        mw.after_agent.assert_called_once()
        assert result.output_data["result"] == "agent result"

    @pytest.mark.asyncio
    async def test_execute_with_agent_error(self):
        """测试 Agent 执行错误"""
        mw = self._create_mock_middleware()
        chain = MiddlewareChain([mw])

        async def failing_agent_func():
            raise Exception("agent failed")

        state = MiddlewareState(agent_id="test", task_id="task-1")
        result = await chain.execute(state, failing_agent_func)

        assert result.error == "agent failed"
        # after_agent 仍然应该被调用
        mw.after_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_middlewares(self):
        """测试列出中间件"""

        class TestMW(Middleware):
            async def before_agent(self, state):
                return state

            async def after_agent(self, state):
                return state

        chain = MiddlewareChain()
        chain.add(TestMW())
        chain.add(TestMW())

        names = chain.list_middlewares()
        assert names == ["TestMW", "TestMW"]


class TestContextMiddleware:
    """ContextMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_before_creates_context(self):
        """测试 before 创建上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_manager = ContextManager(workspace_dir=tmpdir)
            middleware = ContextMiddleware(context_manager=context_manager)

            state = MiddlewareState(
                agent_id="analyst",
                task_id="task-1",
                input_data={"requirement": "测试"},
            )
            result = await middleware.before_agent(state)

            assert "context_workspace" in result.metadata
            assert result.metadata["context_workspace"].startswith(tmpdir)

    @pytest.mark.asyncio
    async def test_after_clears_context(self):
        """测试 after 清理上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_manager = ContextManager(workspace_dir=tmpdir)
            middleware = ContextMiddleware(context_manager=context_manager)

            state = MiddlewareState(agent_id="analyst", task_id="task-1")
            # 先创建上下文
            await middleware.before_agent(state)

            # 清理
            result = await middleware.after_agent(state)
            ctx = context_manager.get_context("analyst", "task-1")
            assert ctx is None

    @pytest.mark.asyncio
    async def test_skips_without_agent_id(self):
        """测试没有 agent_id 时跳过"""
        middleware = ContextMiddleware()
        state = MiddlewareState(agent_id="", task_id="task-1")
        result = await middleware.before_agent(state)
        assert result == state


class TestSummarizationMiddleware:
    """SummarizationMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_compresses_long_output(self):
        """测试压缩长输出"""
        middleware = SummarizationMiddleware(max_output_length=100)

        state = MiddlewareState()
        state.output_data["result"] = "x" * 200
        result = await middleware.after_agent(state)

        assert result.metadata["summarized"] is True
        assert len(result.output_data["result"]) <= 100

    @pytest.mark.asyncio
    async def test_does_not_compress_short_output(self):
        """测试不压缩短输出"""
        middleware = SummarizationMiddleware(max_output_length=100)

        state = MiddlewareState()
        state.output_data["result"] = "short text"
        result = await middleware.after_agent(state)

        assert "summarized" not in result.metadata
        assert result.output_data["result"] == "short text"

    @pytest.mark.asyncio
    async def test_before_is_noop(self):
        """测试 before 无操作"""
        middleware = SummarizationMiddleware()
        state = MiddlewareState()
        result = await middleware.before_agent(state)
        assert result == state


class TestErrorHandlingMiddleware:
    """ErrorHandlingMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_retries_on_error(self):
        """测试错误重试"""
        middleware = ErrorHandlingMiddleware(max_retries=3, base_delay=0.01)

        state = MiddlewareState(agent_id="test", task_id="task-1", error="API error")
        result = await middleware.after_agent(state)

        # 第一次重试，错误应该被清除
        assert result.error is None
        assert result.metadata["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        middleware = ErrorHandlingMiddleware(max_retries=1, base_delay=0.01)

        # 第一次失败
        state = MiddlewareState(agent_id="test", task_id="task-1", error="error 1")
        state = await middleware.after_agent(state)
        assert state.error is None  # 重试，错误被清除

        # 第二次失败（实际应该由上层重新设置错误）
        state.error = "error 2"
        state = await middleware.after_agent(state)
        assert state.error == "error 2"  # 超过最大重试次数，保留错误
        assert state.metadata["max_retries_exceeded"] is True

    @pytest.mark.asyncio
    async def test_clears_retry_on_success(self):
        """测试成功后清除重试计数"""
        middleware = ErrorHandlingMiddleware(max_retries=3)

        # 先失败一次
        state = MiddlewareState(agent_id="test", task_id="task-1", error="error")
        await middleware.after_agent(state)

        # 然后成功
        state.error = None
        result = await middleware.after_agent(state)
        assert result.error is None


class TestStatePersistenceMiddleware:
    """StatePersistenceMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_saves_state_after_execution(self):
        """测试执行后保存状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = StatePersistenceMiddleware(persistence_dir=tmpdir)

            state = MiddlewareState(
                agent_id="test",
                task_id="task-1",
                metadata={"key": "value"},
            )
            result = await middleware.after_agent(state)

            # 检查文件是否存在
            state_files = list(Path(tmpdir).glob("*.json"))
            assert len(state_files) == 1

    @pytest.mark.asyncio
    async def test_clears_state(self):
        """测试清理状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = StatePersistenceMiddleware(persistence_dir=tmpdir)

            state = MiddlewareState(agent_id="test", task_id="task-1")
            await middleware.after_agent(state)

            middleware.clear_state("test", "task-1")
            state_files = list(Path(tmpdir).glob("*.json"))
            assert len(state_files) == 0


class TestAuditMiddleware:
    """AuditMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_records_audit_info(self):
        """测试记录审计信息"""
        middleware = AuditMiddleware()

        state = MiddlewareState(agent_id="test", task_id="task-1")
        state = await middleware.before_agent(state)
        result = await middleware.after_agent(state)

        assert "audit" in result.metadata
        audit = result.metadata["audit"]
        assert audit["agent_id"] == "test"
        assert audit["task_id"] == "task-1"
        assert audit["status"] == "success"
        assert audit["duration"] >= 0

    @pytest.mark.asyncio
    async def test_records_failure(self):
        """测试记录失败"""
        middleware = AuditMiddleware()

        state = MiddlewareState(
            agent_id="test",
            task_id="task-1",
            error="test error",
        )
        state = await middleware.before_agent(state)
        result = await middleware.after_agent(state)

        assert result.metadata["audit"]["status"] == "failed"
        assert result.metadata["audit"]["error"] == "test error"
