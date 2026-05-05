"""工作流管理器

提供高层工作流管理接口，包括启动、暂停、恢复、查询状态等。
"""

import uuid
from datetime import datetime
from typing import Optional

from pm_workstation.models.core import (
    StructuredRequirement,
    WorkflowRun,
    WorkflowStatus,
)
from pm_workstation.orchestrator.workflow_graph import create_workflow_app
from pm_workstation.orchestrator.workflow_state import WorkflowState


class WorkflowManager:
    """工作流管理器

    管理工作流的生命周期，提供启动、暂停、恢复、查询等接口。
    """

    def __init__(self, llm_handler=None) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._llm_handler = llm_handler
        self._app = create_workflow_app(llm_handler=llm_handler)

    def start_workflow(
        self,
        user_id: str,
        requirement_text: str,
        workflow_id: Optional[str] = None,
        llm_provider_id: Optional[str] = None,
    ) -> WorkflowRun:
        """启动新的工作流

        Args:
            user_id: 用户ID
            requirement_text: 原始需求文本
            workflow_id: 可选的工作流ID，不提供则自动生成

        Returns:
            工作流运行记录
        """
        run_id = workflow_id or f"wf-{uuid.uuid4().hex[:12]}"

        run = WorkflowRun(
            id=run_id,
            user_id=user_id,
            requirement_text=requirement_text,
            status=WorkflowStatus.INIT,
        )
        self._runs[run_id] = run

        return run

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowRun]:
        """获取工作流当前状态

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流运行记录，如果不存在则返回 None
        """
        return self._runs.get(workflow_id)

    def pause_workflow(self, workflow_id: str) -> bool:
        """暂停工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            是否成功暂停
        """
        run = self._runs.get(workflow_id)
        if not run:
            return False

        if run.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            return False

        run.update_status(WorkflowStatus.WAITING_USER_INPUT)
        return True

    def resume_workflow(self, workflow_id: str, user_responses: Optional[list] = None) -> bool:
        """恢复工作流

        Args:
            workflow_id: 工作流ID
            user_responses: 用户的澄清回复

        Returns:
            是否成功恢复
        """
        run = self._runs.get(workflow_id)
        if not run:
            return False

        if run.status not in (WorkflowStatus.WAITING_USER_INPUT, WorkflowStatus.FAILED):
            return False

        run.update_status(WorkflowStatus.PARSING)
        return True

    def get_deliverables(self, workflow_id: str) -> Optional[dict]:
        """获取工作流交付物

        Args:
            workflow_id: 工作流ID

        Returns:
            交付物字典，包含 prototype_url、prd_document_url、verification_report 等
        """
        run = self._runs.get(workflow_id)
        if not run:
            return None

        deliverables = {
            "prototype_url": run.prototype_url,
            "prd_document_url": run.prd_document_url,
            "verification_report": run.verification_report,
        }
        return deliverables

    def list_workflows(self, user_id: Optional[str] = None) -> list[WorkflowRun]:
        """列出工作流

        Args:
            user_id: 可选的用户ID过滤

        Returns:
            工作流运行记录列表
        """
        if user_id:
            return [r for r in self._runs.values() if r.user_id == user_id]
        return list(self._runs.values())

    def _build_initial_state(self, run: WorkflowRun) -> WorkflowState:
        """构建初始工作流状态

        Args:
            run: 工作流运行记录

        Returns:
            初始工作流状态
        """
        return WorkflowState(
            workflow_run=run,
        )

    def _update_run_from_state(self, state: WorkflowState) -> None:
        """从工作流状态更新运行记录

        Args:
            state: 工作流状态
        """
        run = self._runs.get(state.workflow_run.id)
        if run:
            run.status = state.workflow_run.status
            run.updated_at = state.workflow_run.updated_at
            run.structured_requirement = state.structured_requirement
            run.prototype_url = "prototype.html" if state.prototype_html else None
            run.prd_document_url = "prd.md" if state.prd_document else None
            run.verification_report = state.verification_report
            run.error_message = state.error_message
