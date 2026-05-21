"""Workflow API - 工作流 API 路由

提供工作流列表查询、执行、进度查询等 API。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.agents.pm_sub_agents import register_pm_sub_agents
from pm_workstation.agents.sub_agent_registry import get_sub_agent_registry
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.workflow.pm_workflows import (
    get_all_workflows,
    get_workflow_by_id,
    search_workflows,
)
from pm_workstation.workflow.workflow_models import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowProgress,
    WorkflowTemplate,
)
from pm_workstation.workflow.workflow_orchestrator import (
    get_workflow_orchestrator,
    reset_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow-templates", tags=["工作流编排"])


def _workflow_to_template(workflow: WorkflowDefinition) -> WorkflowTemplate:
    """将工作流定义转换为模板"""
    return WorkflowTemplate(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        category=workflow.category,
        steps_count=len(workflow.steps),
        estimated_time=workflow.estimated_time,
        best_for=workflow.best_for,
        tags=workflow.tags,
        preview_steps=[s.name for s in workflow.steps],
    )


@router.get("", summary="获取工作流列表")
async def list_workflows() -> dict:
    """获取所有预定义工作流模板（无需认证）"""
    workflows = get_all_workflows()
    
    return {
        "workflows": [_workflow_to_template(w).model_dump() for w in workflows],
        "total": len(workflows),
        "categories": list(set(w.category for w in workflows)),
    }


@router.get("/search", summary="搜索工作流")
async def search_workflows_api(query: str) -> dict:
    """搜索工作流（无需认证）
    
    Args:
        query: 搜索关键词
    """
    workflows = search_workflows(query)
    
    return {
        "workflows": [_workflow_to_template(w).model_dump() for w in workflows],
        "total": len(workflows),
        "query": query,
    }


@router.get("/category/{category}", summary="按分类获取工作流")
async def list_workflows_by_category(category: str) -> dict:
    """获取指定分类的工作流（无需认证）"""
    from pm_workstation.workflow.pm_workflows import get_workflows_by_category
    
    workflows = get_workflows_by_category(category)
    
    return {
        "workflows": [_workflow_to_template(w).model_dump() for w in workflows],
        "total": len(workflows),
        "category": category,
    }


@router.get("/categories", summary="获取工作流分类")
async def list_categories() -> dict:
    """获取所有工作流分类（无需认证）"""
    workflows = get_all_workflows()
    
    categories = {}
    for w in workflows:
        if w.category not in categories:
            categories[w.category] = {
                "name": w.category,
                "workflows_count": 0,
                "description": _get_category_description(w.category),
            }
        categories[w.category]["workflows_count"] += 1
    
    return {
        "categories": list(categories.values()),
        "total": len(categories),
    }


@router.get("/{workflow_id}", summary="获取工作流详情")
async def get_workflow_detail(workflow_id: str) -> dict:
    """获取工作流的详细信息（无需认证）"""
    workflow = get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return workflow.model_dump()


@router.post("/{workflow_id}/execute", summary="执行工作流")
async def execute_workflow(
    workflow_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """执行预定义工作流
    
    Args:
        workflow_id: 工作流 ID
        body: 包含 initial_input（可选）、session_id（可选）
    """
    workflow = get_workflow_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 确保 Sub-Agents 已注册
    if len(get_sub_agent_registry().list_all()) == 0:
        register_pm_sub_agents()
    
    orchestrator = get_workflow_orchestrator()
    
    initial_input = body.get("initial_input", {})
    session_id = body.get("session_id")
    
    # 执行工作流
    execution = await orchestrator.execute_workflow(
        workflow=workflow,
        user_id=user_id,
        session_id=session_id,
        initial_input=initial_input,
    )
    
    return {
        "execution_id": execution.execution_id,
        "workflow_id": execution.workflow_id,
        "workflow_name": execution.workflow_name,
        "status": execution.status.value,
        "total_steps": execution.total_steps,
        "completed_steps": execution.completed_steps,
        "failed_steps": execution.failed_steps,
        "total_duration_ms": execution.total_duration_ms,
        "artifacts": execution.final_artifacts,
        "steps_results": [
            {
                "step_id": r.step_id,
                "step_name": r.step_name,
                "status": r.status.value,
                "duration_ms": r.duration_ms,
                "agent_name": r.agent_name,
            }
            for r in execution.steps_results
        ],
        "started_at": execution.started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "error_message": execution.error_message,
    }


@router.get("/execution/{execution_id}", summary="获取执行记录")
async def get_execution(execution_id: str) -> dict:
    """获取工作流执行记录
    
    Args:
        execution_id: 执行 ID
    """
    orchestrator = get_workflow_orchestrator()
    progress = orchestrator.get_progress(execution_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    return {
        "execution_id": progress.execution_id,
        "workflow_id": progress.workflow_id,
        "workflow_name": progress.workflow_name,
        "status": progress.status.value,
        "progress_percent": progress.progress_percent,
        "current_step": progress.current_step,
        "current_step_status": progress.current_step_status.value if progress.current_step_status else None,
        "completed_steps": progress.completed_steps,
        "running_steps": progress.running_steps,
        "pending_steps": progress.pending_steps,
        "failed_steps": progress.failed_steps,
        "artifacts_generated": progress.artifacts_generated,
        "estimated_remaining_time": progress.estimated_remaining_time,
    }


@router.get("/execution/{execution_id}/progress", summary="获取执行进度")
async def get_execution_progress(execution_id: str) -> dict:
    """获取工作流执行进度（用于轮询）
    
    Args:
        execution_id: 执行 ID
    """
    orchestrator = get_workflow_orchestrator()
    progress = orchestrator.get_progress(execution_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    return {
        "execution_id": progress.execution_id,
        "status": progress.status.value,
        "progress_percent": progress.progress_percent,
        "current_step": progress.current_step,
        "running_steps": len(progress.running_steps),
        "artifacts_count": len(progress.artifacts_generated),
    }


@router.get("/execution/{execution_id}/artifacts", summary="获取执行产物")
async def get_execution_artifacts(execution_id: str) -> dict:
    """获取工作流执行的产物列表
    
    Args:
        execution_id: 执行 ID
    """
    from pm_workstation.artifact.artifact_manager import get_artifact_manager
    
    manager = get_artifact_manager()
    artifacts = await manager.list_by_workflow_execution(execution_id)
    
    return {
        "execution_id": execution_id,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "type": a.type.value,
                "current_version": a.current_version,
                "preview_url": a.preview_url,
                "download_url": a.download_url,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


def _get_category_description(category: str) -> str:
    """获取分类描述"""
    descriptions = {
        "product-design": "产品设计相关工作流，包括需求分析、原型设计、PRD撰写等",
        "market-research": "市场调研相关工作流，包括市场分析、竞品研究、战略规划等",
        "user-research": "用户研究相关工作流，包括访谈设计、用户旅程、用户画像等",
        "strategy": "战略规划相关工作流，包括商业模式、定位策略、市场进入等",
        "analytics": "数据分析相关工作流，包括指标设计、数据分析、A/B测试等",
    }
    return descriptions.get(category, "")