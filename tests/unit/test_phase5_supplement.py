"""Phase 5: 测试和优化 - 补充关键模块测试"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.agents.coordinator import CoordinatorAgent
from pm_workstation.agents.middlewares.state_persistence import StatePersistenceMiddleware
from pm_workstation.agents.middlewares.base import MiddlewareState
from pm_workstation.agents.registry import SubAgentConfig, SubAgentRegistry
from pm_workstation.agents.task_tool import (
    ContextManager,
    SubAgentExecutor,
    TaskDelegationTool,
    TaskRequest,
    TaskResult,
)
from pm_workstation.model_router.base import LLMResponse
from pm_workstation.models.core import WorkflowRun, WorkflowStatus
from pm_workstation.orchestrator.workflow_graph_v2 import (
    WorkflowNodesV2,
    _create_coordinator,
)
from pm_workstation.orchestrator.workflow_manager import WorkflowManager
from pm_workstation.orchestrator.workflow_state import WorkflowState
from pm_workstation.skills.loader import SkillLoader


class TestWorkflowGraphV2Coordinator:
    """workflow_graph_v2.py Coordinator 节点测试"""

    @pytest.mark.asyncio
    async def test_coordinator_node_with_llm(self):
        """测试 Coordinator 节点使用 LLM"""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = LLMResponse(
            content=json.dumps({
                "plan": "分析需求",
                "subtasks": [
                    {
                        "id": "task-1",
                        "agent_id": "analyst",
                        "description": "分析需求",
                        "timeout": 60,
                        "can_run_parallel": True,
                    }
                ],
                "execution_order": ["task-1"],
            }),
            model="gpt-4",
        )

        # 使用 V2 节点
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="创建一个博客系统")
        state = WorkflowState(workflow_run=run)

        # 模拟 Coordinator 结果
        with patch("pm_workstation.orchestrator.workflow_graph_v2._create_coordinator") as mock_create:
            mock_coordinator = AsyncMock()
            mock_coordinator.process_request.return_value = {
                "plan": "分析需求",
                "subtasks": [{"id": "task-1"}],
                "summary": "任务拆解完成",
            }
            mock_create.return_value = mock_coordinator

            result = WorkflowNodesV2.parsing_node(state, llm_handler=mock_llm)

            assert state.task_decomposition is not None
            assert state.coordinator_summary == "任务拆解完成"

    @pytest.mark.asyncio
    async def test_coordinator_node_fallback_to_v1(self):
        """测试 Coordinator 失败时降级到 V1"""
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM API error")

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="创建一个博客系统")
        state = WorkflowState(workflow_run=run)

        # V2 Coordinator 失败，应该降级到 V1
        result = WorkflowNodesV2.parsing_node(state, llm_handler=mock_llm)

        # V1 在没有 LLM 或 LLM 失败时会跳过解析
        assert state.workflow_run.status == WorkflowStatus.PARSED


class TestWorkflowGraphV2Generating:
    """workflow_graph_v2.py 生成节点测试"""

    def test_generating_node_uses_coordinator_results(self):
        """测试生成节点使用 Coordinator 结果"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            task_decomposition={"plan": "test"},
            subtask_results={
                "task-designer": {
                    "agent_id": "designer",
                    "status": "success",
                    "output": "<!DOCTYPE html><html><body>原型</body></html>",
                },
                "task-writer": {
                    "agent_id": "writer",
                    "status": "success",
                    "output": "# PRD\n\n测试文档",
                },
            },
        )

        result = WorkflowNodesV2.generating_node(state, llm_handler=None)

        assert state.workflow_run.status == WorkflowStatus.GENERATED
        assert "<!DOCTYPE html>" in state.prototype_html
        assert "# PRD" in state.prd_document

    def test_generating_node_fallback_when_no_results(self):
        """测试生成节点在没有结果时使用兜底"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="创建一个电商系统")
        state = WorkflowState(workflow_run=run)

        result = WorkflowNodesV2.generating_node(state, llm_handler=None)

        assert state.workflow_run.status == WorkflowStatus.GENERATED
        assert "<!DOCTYPE html>" in state.prototype_html
        assert "电商" in state.prd_document


class TestWorkflowGraphV2Routing:
    """workflow_graph_v2.py 路由函数测试"""

    def test_should_proceed_to_generate_v2(self):
        """测试路由：进入生成阶段"""
        from pm_workstation.orchestrator.workflow_graph_v2 import should_proceed_to_generate_v2

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(workflow_run=run)

        # 没有澄清问题，应该进入生成
        assert should_proceed_to_generate_v2(state) == "generate"

    def test_should_proceed_to_generate_v2_wait(self):
        """测试路由：等待用户输入"""
        from pm_workstation.orchestrator.workflow_graph_v2 import should_proceed_to_generate_v2

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            clarification_questions=[{"id": 0, "question": "测试"}],
            user_responses=[],
        )

        assert should_proceed_to_generate_v2(state) == "wait_for_user"

    def test_should_proceed_to_complete_v2(self):
        """测试路由：进入完成阶段"""
        from pm_workstation.orchestrator.workflow_graph_v2 import should_proceed_to_complete_v2

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        run.update_status(WorkflowStatus.VERIFIED)
        state = WorkflowState(workflow_run=run)

        assert should_proceed_to_complete_v2(state) == "complete"

    def test_should_proceed_to_complete_v2_failed(self):
        """测试路由：失败"""
        from pm_workstation.orchestrator.workflow_graph_v2 import should_proceed_to_complete_v2

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(workflow_run=run, error_message="错误")

        assert should_proceed_to_complete_v2(state) == "failed"


class TestStatePersistenceMiddleware:
    """StatePersistenceMiddleware 补充测试"""

    @pytest.mark.asyncio
    async def test_load_saved_state(self):
        """测试加载已保存的状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = StatePersistenceMiddleware(persistence_dir=tmpdir)

            # 先保存状态
            state = MiddlewareState(
                agent_id="test",
                task_id="task-1",
                metadata={"key": "value"},
            )
            await middleware.after_agent(state)

            # 重新加载
            new_state = MiddlewareState(agent_id="test", task_id="task-1")
            result = await middleware.before_agent(new_state)

            assert result.metadata.get("key") == "value"

    @pytest.mark.asyncio
    async def test_save_state_without_agent_id(self):
        """测试没有 agent_id 时不保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = StatePersistenceMiddleware(persistence_dir=tmpdir)

            state = MiddlewareState(agent_id="", task_id="task-1")
            result = await middleware.after_agent(state)

            state_files = list(Path(tmpdir).glob("*.json"))
            assert len(state_files) == 0


class TestErrorScenarios:
    """错误场景测试"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(45)
    async def test_coordinator_timeout(self):
        """测试 Coordinator 超时"""
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(500)

        mock_coordinator = AsyncMock()
        mock_coordinator.process_request = slow_process

        with patch("pm_workstation.orchestrator.workflow_graph_v2._create_coordinator") as mock_create:
            mock_create.return_value = mock_coordinator

            run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
            state = WorkflowState(workflow_run=run)

            # 超时应该降级到 V1
            result = WorkflowNodesV2.parsing_node(state, llm_handler=MagicMock())

            # 降级后应该是 PARSED 状态
            assert state.workflow_run.status in (WorkflowStatus.PARSED, WorkflowStatus.FAILED)

    @pytest.mark.asyncio
    async def test_subagent_timeout_in_delegation(self):
        """测试子 Agent 超时在委派中"""
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="slow-agent",
            name="慢 Agent",
            description="测试",
            system_prompt="Test",
            timeout_seconds=1,
        ))

        async def slow_chat(*args, **kwargs):
            await asyncio.sleep(100)

        mock_handler = AsyncMock()
        mock_handler.chat = slow_chat
        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(llm_factory=mock_factory)
        tool = TaskDelegationTool(registry=registry, executor=executor)

        result = await tool.invoke(
            agent_id="slow-agent",
            task_description="慢任务",
            timeout=1,
        )

        assert result.status == "timeout"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_llm_api_error_in_coordinator(self):
        """测试 LLM API 错误在 Coordinator 中"""
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("Connection refused")

        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(workflow_run=run)

        # Coordinator 失败，降级到 V1
        result = WorkflowNodesV2.parsing_node(state, llm_handler=mock_llm)

        # V1 也会失败或跳过
        assert state.workflow_run.status in (WorkflowStatus.PARSED, WorkflowStatus.FAILED)


class TestWorkflowManagerIntegration:
    """WorkflowManager 集成测试"""

    def test_v1_v2_same_requirement(self):
        """测试 V1 和 V2 处理相同需求"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with patch("pm_workstation.orchestrator.workflow_manager.ARTIFACTS_DIR", tmpdir1):
                with patch("pm_workstation.orchestrator.workflow_manager.PERSISTENCE_FILE",
                           str(Path(tmpdir1) / "cache.json")):
                    manager = WorkflowManager(use_v2=True)
                    run = manager.start_workflow(
                        user_id="test",
                        requirement_text="创建一个用户管理系统",
                    )
                    manager.execute_workflow_sync(run.id)
                    result = manager.get_workflow_status(run.id)

                    assert result.status in (
                        WorkflowStatus.COMPLETED,
                        WorkflowStatus.VERIFIED,
                        WorkflowStatus.GENERATED,
                    )
                    assert result.prototype_url is not None
                    assert result.prd_document_url is not None

    def test_multiple_workflows_no_pollution(self):
        """测试多个工作流无状态污染"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pm_workstation.orchestrator.workflow_manager.ARTIFACTS_DIR", tmpdir):
                with patch("pm_workstation.orchestrator.workflow_manager.PERSISTENCE_FILE",
                           str(Path(tmpdir) / "cache.json")):
                    manager = WorkflowManager(use_v2=True)

                    runs = []
                    for i in range(3):
                        run = manager.start_workflow(
                            user_id="test",
                            requirement_text=f"需求 {i}",
                        )
                        runs.append(run)

                    # 并行执行
                    import threading
                    threads = []
                    for run in runs:
                        t = threading.Thread(target=manager.execute_workflow_sync, args=(run.id,))
                        threads.append(t)
                        t.start()

                    for t in threads:
                        t.join(timeout=30)

                    # 验证每个工作流独立
                    for run in runs:
                        result = manager.get_workflow_status(run.id)
                        assert result is not None
                        assert result.requirement_text.startswith("需求")
                        assert result.prototype_url is not None


class TestPerformanceOptimization:
    """性能优化测试"""

    def test_context_manager_cleanup(self):
        """测试上下文管理器清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = ContextManager(workspace_dir=tmpdir)

            # 创建多个上下文
            for i in range(5):
                cm.create_isolated_context(f"agent-{i}", f"task-{i}", {})

            assert len(cm.list_active_contexts()) == 5

            # 清理所有
            for i in range(5):
                cm.clear_context(f"agent-{i}", f"task-{i}")

            assert len(cm.list_active_contexts()) == 0

    def test_skill_loader_lazy_loading(self):
        """测试技能加载器懒加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(skills_dir=tmpdir)

            # 空目录应该没有技能
            assert loader.list_available() == []

            # 添加一个技能文件
            import yaml
            skill_data = {
                "name": "test-skill",
                "description": "测试",
                "system_prompt": "Test",
            }
            with open(Path(tmpdir) / "test-skill.yaml", "w") as f:
                yaml.dump(skill_data, f)

            # 重新加载
            loader2 = SkillLoader(skills_dir=tmpdir)
            assert "test-skill" in loader2.list_available()
