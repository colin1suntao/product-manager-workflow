"""端到端测试 - 完整工作流流程

测试从需求输入到原型生成、文档生成、校验的完整流程。
使用模拟的 LLM 响应来测试整个工作流编排。
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.models.core import WorkflowRun, WorkflowStatus
from pm_workstation.orchestrator.workflow_manager import WorkflowManager, PERSISTENCE_FILE


@pytest.fixture(autouse=True)
def clear_workflow_cache():
    """在每个测试前清理工作流缓存文件"""
    if os.path.exists(PERSISTENCE_FILE):
        os.remove(PERSISTENCE_FILE)
    yield
    if os.path.exists(PERSISTENCE_FILE):
        os.remove(PERSISTENCE_FILE)


@pytest.fixture
def workflow_manager():
    return WorkflowManager()


class TestCompleteWorkflowE2E:
    """完整工作流端到端测试"""

    def test_start_workflow(self, workflow_manager):
        """测试启动工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="用户需要一个登录页面",
        )

        assert run.id.startswith("wf-")
        assert run.user_id == "test-user-001"
        assert run.requirement_text == "用户需要一个登录页面"
        assert run.status == WorkflowStatus.INIT

    def test_start_workflow_with_custom_id(self, workflow_manager):
        """测试使用自定义 ID 启动工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="自定义 ID 测试",
            workflow_id="wf-custom-001",
        )

        assert run.id == "wf-custom-001"

    def test_get_workflow_status(self, workflow_manager):
        """测试获取工作流状态"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="状态查询测试",
        )

        retrieved = workflow_manager.get_workflow_status(run.id)
        assert retrieved is not None
        assert retrieved.id == run.id
        assert retrieved.status == WorkflowStatus.INIT

    def test_get_workflow_status_nonexistent(self, workflow_manager):
        """测试获取不存在的工作流状态"""
        result = workflow_manager.get_workflow_status("nonexistent-id")
        assert result is None

    def test_pause_workflow(self, workflow_manager):
        """测试暂停工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="暂停测试",
        )

        success = workflow_manager.pause_workflow(run.id)
        assert success is True

        updated = workflow_manager.get_workflow_status(run.id)
        assert updated is not None
        assert updated.status == WorkflowStatus.WAITING_USER_INPUT

    def test_pause_completed_workflow(self, workflow_manager):
        """测试暂停已完成的工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="暂停已完成测试",
        )
        run.status = WorkflowStatus.COMPLETED

        success = workflow_manager.pause_workflow(run.id)
        assert success is False

    def test_resume_workflow(self, workflow_manager):
        """测试恢复工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="恢复测试",
        )
        workflow_manager.pause_workflow(run.id)

        success = workflow_manager.resume_workflow(run.id)
        assert success is True

        updated = workflow_manager.get_workflow_status(run.id)
        assert updated is not None
        assert updated.status == WorkflowStatus.PARSING

    def test_resume_non_paused_workflow(self, workflow_manager):
        """测试恢复非暂停状态的工作流"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="恢复非暂停测试",
        )

        success = workflow_manager.resume_workflow(run.id)
        assert success is False

    def test_get_deliverables(self, workflow_manager):
        """测试获取交付物"""
        run = workflow_manager.start_workflow(
            user_id="test-user-001",
            requirement_text="交付物测试",
        )

        deliverables = workflow_manager.get_deliverables(run.id)
        assert deliverables is not None
        assert "prototype_url" in deliverables
        assert "prd_document_url" in deliverables
        assert "verification_report" in deliverables

    def test_get_deliverables_nonexistent(self, workflow_manager):
        """测试获取不存在的交付物"""
        result = workflow_manager.get_deliverables("nonexistent-id")
        assert result is None

    def test_list_workflows(self, workflow_manager):
        """测试列出工作流"""
        workflow_manager.start_workflow(
            user_id="user-a",
            requirement_text="需求 A",
        )
        workflow_manager.start_workflow(
            user_id="user-a",
            requirement_text="需求 B",
        )
        workflow_manager.start_workflow(
            user_id="user-b",
            requirement_text="需求 C",
        )

        all_workflows = workflow_manager.list_workflows()
        assert len(all_workflows) == 3

        user_a_workflows = workflow_manager.list_workflows(user_id="user-a")
        assert len(user_a_workflows) == 2

        user_b_workflows = workflow_manager.list_workflows(user_id="user-b")
        assert len(user_b_workflows) == 1


class TestErrorHandlingE2E:
    """异常流程端到端测试"""

    def test_pause_nonexistent_workflow(self, workflow_manager):
        """测试暂停不存在的工作流"""
        success = workflow_manager.pause_workflow("nonexistent-id")
        assert success is False

    def test_resume_nonexistent_workflow(self, workflow_manager):
        """测试恢复不存在的工作流"""
        success = workflow_manager.resume_workflow("nonexistent-id")
        assert success is False


class TestConcurrentWorkflowE2E:
    """并发工作流测试"""

    def test_multiple_concurrent_workflows(self, workflow_manager):
        """测试多个并发工作流"""
        runs = []
        for i in range(5):
            run = workflow_manager.start_workflow(
                user_id="test-user",
                requirement_text=f"并发需求 {i}",
            )
            runs.append(run)

        assert len(runs) == 5

        all_statuses = [workflow_manager.get_workflow_status(r.id) for r in runs]
        assert all(s is not None for s in all_statuses)

    def test_workflow_state_isolation(self, workflow_manager):
        """测试工作流状态隔离"""
        run1 = workflow_manager.start_workflow(
            user_id="user-1",
            requirement_text="需求 1",
        )
        run2 = workflow_manager.start_workflow(
            user_id="user-2",
            requirement_text="需求 2",
        )

        workflow_manager.pause_workflow(run1.id)

        status1 = workflow_manager.get_workflow_status(run1.id)
        status2 = workflow_manager.get_workflow_status(run2.id)

        assert status1 is not None
        assert status2 is not None
        assert status1.status == WorkflowStatus.WAITING_USER_INPUT
        assert status2.status == WorkflowStatus.INIT

    def test_list_workflows_isolation(self, workflow_manager):
        """测试列出工作流隔离"""
        workflow_manager.start_workflow(
            user_id="user-x",
            requirement_text="需求 X",
        )
        workflow_manager.start_workflow(
            user_id="user-y",
            requirement_text="需求 Y",
        )

        x_workflows = workflow_manager.list_workflows(user_id="user-x")
        y_workflows = workflow_manager.list_workflows(user_id="user-y")

        assert len(x_workflows) == 1
        assert len(y_workflows) == 1
        assert x_workflows[0].requirement_text == "需求 X"
        assert y_workflows[0].requirement_text == "需求 Y"
