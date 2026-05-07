"""工作流管理器

提供高层工作流管理接口，包括启动、暂停、恢复、查询状态等。
"""

import json
import os
import uuid
from datetime import UTC, datetime

from pm_workstation.models.core import (
    WorkflowRun,
    WorkflowStatus,
)
from pm_workstation.orchestrator.workflow_graph import create_workflow_app
from pm_workstation.orchestrator.workflow_state import WorkflowState

PERSISTENCE_FILE = os.path.join(os.path.dirname(__file__), ".workflow_cache.json")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")


class WorkflowManager:
    """工作流管理器

    管理工作流的生命周期，提供启动、暂停、恢复、查询等接口。
    """

    def __init__(self, llm_handler=None) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._llm_handler = llm_handler
        self._app = create_workflow_app(llm_handler=llm_handler)
        self._load_from_file()
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    def _persistence_path(self) -> str:
        return PERSISTENCE_FILE

    def _load_from_file(self) -> None:
        path = self._persistence_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for item in data:
                run = WorkflowRun(**item)
                self._runs[run.id] = run
        except Exception:
            pass

    def _save_to_file(self) -> None:
        path = self._persistence_path()
        try:
            data = []
            for run in self._runs.values():
                d = run.model_dump(mode="json")
                data.append(d)
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _save_artifact(self, workflow_id: str, filename: str, content: str) -> str:
        """保存产物到文件

        Args:
            workflow_id: 工作流ID
            filename: 文件名
            content: 文件内容

        Returns:
            产物访问路径
        """
        wf_dir = os.path.join(ARTIFACTS_DIR, workflow_id)
        os.makedirs(wf_dir, exist_ok=True)
        filepath = os.path.join(wf_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"/artifacts/{workflow_id}/{filename}"

    def start_workflow(
        self,
        user_id: str,
        requirement_text: str,
        workflow_id: str | None = None,
        llm_provider_id: str | None = None,
    ) -> WorkflowRun:
        """启动新的工作流

        Args:
            user_id: 用户ID
            requirement_text: 原始需求文本
            workflow_id: 可选的工作流ID，不提供则自动生成
            llm_provider_id: LLM Provider ID

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
        self._save_to_file()

        return run

    def execute_workflow_sync(self, run_id: str) -> None:
        """同步执行工作流（用于后台线程）"""
        print(f"[WorkflowManager] Starting execute_workflow_sync for {run_id}")
        run = self._runs.get(run_id)
        if not run:
            print(f"[WorkflowManager] Run {run_id} not found")
            return

        state = WorkflowState(workflow_run=run)
        print("[WorkflowManager] Created initial state")

        try:
            # 使用 LangGraph 执行完整工作流
            print("[WorkflowManager] Invoking LangGraph app...")
            result = self._app.invoke(state)
            print(f"[WorkflowManager] LangGraph completed, result type: {type(result)}")

            # LangGraph 返回的可能是 dict 或 WorkflowState
            if isinstance(result, dict):
                final_state = WorkflowState.model_validate(result)
            else:
                final_state = result

            print(f"[WorkflowManager] Final status: {final_state.workflow_run.status}")

            # 更新运行记录
            self._update_run_from_state(final_state)

            # 保存产物
            workflow_id = run.id
            if final_state.prototype_html:
                print(f"[WorkflowManager] Saving prototype ({len(final_state.prototype_html)} chars)")
                run.prototype_url = self._save_artifact(
                    workflow_id, "prototype.html", final_state.prototype_html,
                )
            if final_state.prd_document:
                print(f"[WorkflowManager] Saving PRD ({len(final_state.prd_document)} chars)")
                run.prd_document_url = self._save_artifact(
                    workflow_id, "prd.md", final_state.prd_document,
                )
            if final_state.verification_report:
                report_dict = final_state.verification_report.model_dump(mode='json')
                report_content = json.dumps(report_dict, ensure_ascii=False, indent=2)
                run.verification_report_url = self._save_artifact(
                    workflow_id, "report.json", report_content,
                )

            self._save_to_file()
            print(f"[WorkflowManager] Workflow {run_id} completed successfully")

        except Exception as e:
            import traceback
            print(f"[WorkflowManager] ERROR in execute_workflow_sync: {e}")
            traceback.print_exc()
            run.status = WorkflowStatus.FAILED
            run.error_message = str(e)
            run.updated_at = datetime.now(UTC)
            self._save_to_file()

    def get_workflow_status(self, workflow_id: str) -> WorkflowRun | None:
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
        self._save_to_file()
        return True

    def resume_workflow(self, workflow_id: str, user_responses: list | None = None) -> bool:
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
        self._save_to_file()
        return True

    def get_deliverables(self, workflow_id: str) -> dict | None:
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

    def list_workflows(self, user_id: str | None = None) -> list[WorkflowRun]:
        """列出工作流

        Args:
            user_id: 可选的用户ID过滤

        Returns:
            工作流运行记录列表
        """
        if user_id:
            return [r for r in self._runs.values() if r.user_id == user_id]
        return list(self._runs.values())

    def cancel_workflow(self, workflow_id: str) -> bool:
        """停止工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            是否成功停止
        """
        run = self._runs.get(workflow_id)
        if not run:
            return False

        if run.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            return False

        run.update_status(WorkflowStatus.CANCELLED)
        self._save_to_file()
        return True

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            是否成功删除
        """
        if workflow_id not in self._runs:
            return False

        del self._runs[workflow_id]
        self._save_to_file()
        return True

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

            # 安全地更新 structured_requirement（可能包含无效数据）
            try:
                run.structured_requirement = state.structured_requirement
            except Exception:
                run.structured_requirement = None

            run.verification_report = state.verification_report
            run.error_message = state.error_message
            self._save_to_file()
