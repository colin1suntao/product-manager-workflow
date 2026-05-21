"""工作流 API 路由

提供工作流管理相关的 REST API 接口。
"""

import threading

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.api.dependencies import get_workflow_manager
from pm_workstation.api.schemas import (
    DeliverablesResponse,
    PauseWorkflowRequest,
    ResumeWorkflowRequest,
    StartWorkflowRequest,
    WorkflowListResponse,
    WorkflowResponse,
)
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.orchestrator.workflow_manager import WorkflowManager

router = APIRouter(prefix="/workflows")


def _convert_run_to_response(run) -> WorkflowResponse:
    """将 WorkflowRun 转换为 WorkflowResponse"""
    return WorkflowResponse(
        id=run.id,
        user_id=run.user_id,
        requirement_text=run.requirement_text,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        structured_requirement=run.structured_requirement.model_dump() if run.structured_requirement else None,
        prototype_url=run.prototype_url,
        prd_document_url=run.prd_document_url,
        verification_report=run.verification_report.model_dump() if run.verification_report else None,
        verification_report_url=run.verification_report_url,
        error_message=run.error_message,
        selected_skills=run.selected_skills if hasattr(run, 'selected_skills') else [],
        llm_provider_id=run.llm_provider_id if hasattr(run, 'llm_provider_id') else None,
    )


@router.post("", response_model=WorkflowResponse, summary="启动工作流")
async def start_workflow(
    workflow_request: StartWorkflowRequest,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowResponse:
    """启动新的工作流

    接收原始需求文本，创建并启动一个新的工作流。
    """
    # 创建工作流
    run = manager.start_workflow(
        user_id=user_id,
        requirement_text=workflow_request.requirement_text,
        llm_provider_id=workflow_request.llm_provider_id,
        skills=workflow_request.skills,
    )

    # 在后台线程执行工作流
    thread = threading.Thread(target=manager.execute_workflow_sync, args=(run.id,), daemon=True)
    thread.start()

    return _convert_run_to_response(run)


@router.get("/{workflow_id}", response_model=WorkflowResponse, summary="查询工作流状态")
async def get_workflow_status(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowResponse:
    """查询工作流当前状态

    返回工作流的详细信息，包括当前状态、进度和错误信息。
    """
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _convert_run_to_response(run)


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse, summary="暂停工作流")
async def pause_workflow(
    workflow_id: str,
    pause_request: PauseWorkflowRequest,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowResponse:
    """暂停工作流

    暂停正在执行的工作流，等待用户输入或后续恢复。
    """
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = manager.pause_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause workflow in status: {run.status}",
        )

    return _convert_run_to_response(run)


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse, summary="恢复工作流")
async def resume_workflow(
    workflow_id: str,
    resume_request: ResumeWorkflowRequest,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowResponse:
    """恢复工作流

    恢复已暂停的工作流，可选择附带用户的澄清回复。
    """
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = manager.resume_workflow(
        workflow_id,
        user_responses=resume_request.user_responses,
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume workflow in status: {run.status}",
        )

    return _convert_run_to_response(run)


@router.get("/{workflow_id}/deliverables", response_model=DeliverablesResponse, summary="获取交付物")
async def get_deliverables(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> DeliverablesResponse:
    """获取工作流交付物

    返回生成的原型、PRD 文档和校验报告等信息。
    """
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    deliverables = manager.get_deliverables(workflow_id)
    if not deliverables:
        raise HTTPException(status_code=404, detail=f"No deliverables for workflow {workflow_id}")

    return DeliverablesResponse(
        workflow_id=workflow_id,
        prototype_url=deliverables.get("prototype_url"),
        prd_document_url=deliverables.get("prd_document_url"),
        verification_report=deliverables.get("verification_report"),
    )


@router.get("", response_model=WorkflowListResponse, summary="列出工作流")
async def list_workflows(
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowListResponse:
    """列出用户的所有工作流

    支持按用户ID过滤。
    """
    workflows = manager.list_workflows(user_id=user_id)
    return WorkflowListResponse(
        workflows=[_convert_run_to_response(run) for run in workflows],
        total=len(workflows),
    )


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse, summary="停止工作流")
async def cancel_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> WorkflowResponse:
    """停止工作流"""
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = manager.cancel_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot cancel workflow in status: {run.status}")

    run = manager.get_workflow_status(workflow_id)
    return _convert_run_to_response(run)


@router.delete("/{workflow_id}", summary="删除工作流")
async def delete_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
    manager: WorkflowManager = Depends(get_workflow_manager),
) -> dict:
    """删除工作流"""
    run = manager.get_workflow_status(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = manager.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete workflow")

    return {"message": "Workflow deleted"}
