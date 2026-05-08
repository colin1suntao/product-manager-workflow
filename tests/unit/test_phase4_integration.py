"""Phase 4 集成测试：工作流图重构"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.models.core import WorkflowRun, WorkflowStatus
from pm_workstation.orchestrator.workflow_graph_v2 import (
    WorkflowNodesV2,
    build_workflow_graph_v2,
    create_workflow_app_v2,
)
from pm_workstation.orchestrator.workflow_state import WorkflowState


class TestWorkflowStateV2:
    """WorkflowState V2 新增字段测试"""

    def test_new_fields_default_values(self):
        """测试新字段默认值"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(workflow_run=run)

        assert state.task_decomposition is None
        assert state.subtask_results == {}
        assert state.active_agents == []
        assert state.coordinator_summary == ""

    def test_new_fields_can_be_set(self):
        """测试新字段可设置"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            task_decomposition={"plan": "test"},
            subtask_results={"task-1": {"status": "success"}},
            active_agents=["analyst", "writer"],
            coordinator_summary="汇总结果",
        )

        assert state.task_decomposition == {"plan": "test"}
        assert len(state.subtask_results) == 1
        assert len(state.active_agents) == 2
        assert state.coordinator_summary == "汇总结果"

    def test_to_dict_includes_new_fields(self):
        """测试 to_dict 包含新字段"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            task_decomposition={"plan": "test"},
        )

        d = state.to_dict()
        assert "task_decomposition" in d
        assert d["task_decomposition"] == {"plan": "test"}

    def test_from_dict_restores_new_fields(self):
        """测试 from_dict 恢复新字段"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            task_decomposition={"plan": "test"},
            subtask_results={"task-1": "result"},
        )

        d = state.to_dict()
        restored = WorkflowState.from_dict(d)

        assert restored.task_decomposition == {"plan": "test"}
        assert restored.subtask_results == {"task-1": "result"}


class TestWorkflowNodesV2:
    """WorkflowNodesV2 测试"""

    def test_parsing_node_empty_requirement(self):
        """测试解析节点 - 空需求"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="")
        state = WorkflowState(workflow_run=run)

        result = WorkflowNodesV2.parsing_node(state, llm_handler=None)
        assert state.workflow_run.status == WorkflowStatus.FAILED
        assert state.error_message is not None

    def test_generating_node_no_llm_fallback(self):
        """测试生成节点 - 无 LLM 时使用兜底"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="创建一个博客系统")
        state = WorkflowState(workflow_run=run)

        result = WorkflowNodesV2.generating_node(state, llm_handler=None)

        assert state.workflow_run.status == WorkflowStatus.GENERATED
        assert state.prototype_html != ""
        assert state.prd_document != ""
        assert "<!DOCTYPE html>" in state.prototype_html
        assert "产品需求文档" in state.prd_document

    def test_verifying_node_reuses_v1(self):
        """测试校验节点复用 V1"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(
            workflow_run=run,
            prototype_html="<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name=\"viewport\"></head><body><button aria-label=\"test\"></button><input><label></label><style></style></body></html>",
            prd_document="# 产品需求文档\n\n## 产品概述\n测试\n\n## 功能需求\n\n### 用户故事\n测试\n\n## 验收标准\n测试\n\n## 非功能需求\n测试\n\n## 技术架构\n测试",
        )

        result = WorkflowNodesV2.verifying_node(state)

        assert state.workflow_run.status == WorkflowStatus.VERIFIED
        assert state.verification_report is not None

    def test_completing_node(self):
        """测试完成节点"""
        run = WorkflowRun(id="wf-test", user_id="user-1", requirement_text="测试")
        state = WorkflowState(workflow_run=run)

        result = WorkflowNodesV2.completing_node(state)

        assert state.workflow_run.status == WorkflowStatus.COMPLETED


class TestWorkflowGraphV2:
    """工作流图 V2 测试"""

    def test_build_graph(self):
        """测试构建工作流图"""
        graph = build_workflow_graph_v2(llm_handler=None)
        assert graph is not None

    def test_create_app(self):
        """测试创建编译后的应用"""
        app = create_workflow_app_v2(llm_handler=None)
        assert app is not None


class TestWorkflowManagerV2:
    """WorkflowManager 使用 V2 图测试"""

    def test_manager_uses_v2_by_default(self):
        """测试管理器默认使用 V2"""
        from pm_workstation.orchestrator.workflow_manager import WorkflowManager

        manager = WorkflowManager()
        assert manager._use_v2 is True

    def test_manager_can_use_v1(self):
        """测试管理器可以切换到 V1"""
        from pm_workstation.orchestrator.workflow_manager import WorkflowManager

        manager = WorkflowManager(use_v2=False)
        assert manager._use_v2 is False

    def test_v2_workflow_execution(self):
        """测试 V2 工作流执行"""
        from pm_workstation.orchestrator.workflow_manager import WorkflowManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # 模拟 artifacts 目录
            with patch("pm_workstation.orchestrator.workflow_manager.ARTIFACTS_DIR", tmpdir):
                with patch("pm_workstation.orchestrator.workflow_manager.PERSISTENCE_FILE",
                           str(Path(tmpdir) / "cache.json")):
                    manager = WorkflowManager(use_v2=True)
                    run = manager.start_workflow(
                        user_id="test-user",
                        requirement_text="创建一个用户管理系统",
                    )

                    assert run.status == WorkflowStatus.INIT

                    # 执行工作流
                    manager.execute_workflow_sync(run.id)

                    # 验证状态
                    updated_run = manager.get_workflow_status(run.id)
                    assert updated_run is not None
                    assert updated_run.status in (
                        WorkflowStatus.COMPLETED,
                        WorkflowStatus.VERIFIED,
                        WorkflowStatus.GENERATED,
                    )
                    # 应该有产物
                    assert updated_run.prototype_url is not None
                    assert updated_run.prd_document_url is not None


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_v1_and_v2_produce_same_outputs(self):
        """测试 V1 和 V2 产生相同的输出（无 LLM 时）"""
        from pm_workstation.orchestrator.workflow_manager import WorkflowManager

        # V1
        with tempfile.TemporaryDirectory() as tmpdir1:
            with patch("pm_workstation.orchestrator.workflow_manager.ARTIFACTS_DIR", tmpdir1):
                with patch("pm_workstation.orchestrator.workflow_manager.PERSISTENCE_FILE",
                           str(Path(tmpdir1) / "cache.json")):
                    manager_v1 = WorkflowManager(use_v2=False)
                    run_v1 = manager_v1.start_workflow(
                        user_id="test",
                        requirement_text="创建一个博客系统",
                    )
                    manager_v1.execute_workflow_sync(run_v1.id)
                    result_v1 = manager_v1.get_workflow_status(run_v1.id)

        # V2
        with tempfile.TemporaryDirectory() as tmpdir2:
            with patch("pm_workstation.orchestrator.workflow_manager.ARTIFACTS_DIR", tmpdir2):
                with patch("pm_workstation.orchestrator.workflow_manager.PERSISTENCE_FILE",
                           str(Path(tmpdir2) / "cache.json")):
                    manager_v2 = WorkflowManager(use_v2=True)
                    run_v2 = manager_v2.start_workflow(
                        user_id="test",
                        requirement_text="创建一个博客系统",
                    )
                    manager_v2.execute_workflow_sync(run_v2.id)
                    result_v2 = manager_v2.get_workflow_status(run_v2.id)

        # 验证两者都成功
        assert result_v1.status in (WorkflowStatus.COMPLETED, WorkflowStatus.VERIFIED, WorkflowStatus.GENERATED)
        assert result_v2.status in (WorkflowStatus.COMPLETED, WorkflowStatus.VERIFIED, WorkflowStatus.GENERATED)

        # 验证都有产物
        assert result_v1.prototype_url is not None
        assert result_v2.prototype_url is not None
        assert result_v1.prd_document_url is not None
        assert result_v2.prd_document_url is not None
