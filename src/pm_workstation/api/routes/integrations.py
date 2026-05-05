"""集成配置 API 路由

提供外部系统集成配置和同步任务管理的 REST API 接口。
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.integrations.models import (
    IntegrationConfig,
    IntegrationType,
    SyncDirection,
    SyncStatus,
    SyncTask,
)
from pm_workstation.integrations.store import integration_store, sync_task_store

router = APIRouter(prefix="/integrations")


class IntegrationConfigRequest(BaseModel):
    """集成配置请求模型"""

    name: str
    integration_type: str
    enabled: bool = True
    api_endpoint: str = ""
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    settings: Optional[dict] = None


class SyncTaskRequest(BaseModel):
    """同步任务请求模型"""

    direction: str = "import"
    workflow_id: str = ""
    source_data: Optional[dict] = None


@router.post("/configs", response_model=dict, summary="创建集成配置")
async def create_integration_config(
    request: IntegrationConfigRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建外部系统集成配置

    支持 Jira, Figma, GitHub, GitLab 等系统的配置。
    """
    try:
        integration_type = IntegrationType(request.integration_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid integration type: {request.integration_type}",
        )

    config = IntegrationConfig(
        id=f"int-{uuid.uuid4().hex[:8]}",
        name=request.name,
        integration_type=integration_type,
        enabled=request.enabled,
        api_endpoint=request.api_endpoint,
        api_key=request.api_key,
        api_secret=request.api_secret,
        access_token=request.access_token,
        settings=request.settings,
        created_by=user_id,
    )

    result = integration_store.create_config(config)

    return {
        "id": result.id,
        "name": result.name,
        "integration_type": result.integration_type.value,
        "enabled": result.enabled,
        "api_endpoint": result.api_endpoint,
        "created_at": result.created_at.isoformat(),
    }


@router.get("/configs", response_model=dict, summary="列出集成配置")
async def list_integration_configs(
    integration_type: Optional[str] = Query(default=None, description="集成类型过滤"),
    enabled_only: bool = Query(default=False, description="仅显示启用的配置"),
    user_id: str = Depends(get_current_user),
) -> dict:
    """列出所有外部系统集成配置"""
    type_enum = None
    if integration_type:
        try:
            type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid integration type: {integration_type}",
            )

    configs = integration_store.list_configs(
        integration_type=type_enum,
        enabled_only=enabled_only,
    )

    return {
        "configs": [
            {
                "id": c.id,
                "name": c.name,
                "integration_type": c.integration_type.value,
                "enabled": c.enabled,
                "api_endpoint": c.api_endpoint,
                "created_at": c.created_at.isoformat(),
            }
            for c in configs
        ],
        "total": len(configs),
    }


@router.get("/configs/{config_id}", response_model=dict, summary="获取集成配置")
async def get_integration_config(
    config_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取指定集成配置的详细信息"""
    config = integration_store.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Integration config {config_id} not found")

    return {
        "id": config.id,
        "name": config.name,
        "integration_type": config.integration_type.value,
        "enabled": config.enabled,
        "api_endpoint": config.api_endpoint,
        "settings": config.settings,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }


@router.put("/configs/{config_id}", response_model=dict, summary="更新集成配置")
async def update_integration_config(
    config_id: str,
    request: IntegrationConfigRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """更新集成配置"""
    config = integration_store.update_config(
        config_id,
        name=request.name,
        enabled=request.enabled,
        api_endpoint=request.api_endpoint,
        api_key=request.api_key,
        api_secret=request.api_secret,
        access_token=request.access_token,
        settings=request.settings,
    )

    if not config:
        raise HTTPException(status_code=404, detail=f"Integration config {config_id} not found")

    return {
        "id": config.id,
        "name": config.name,
        "enabled": config.enabled,
        "updated_at": config.updated_at.isoformat(),
    }


@router.delete("/configs/{config_id}", response_model=dict, summary="删除集成配置")
async def delete_integration_config(
    config_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """删除集成配置"""
    success = integration_store.delete_config(config_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Integration config {config_id} not found")

    return {"message": f"Integration config {config_id} deleted successfully"}


@router.post("/configs/{config_id}/sync-tasks", response_model=dict, summary="创建同步任务")
async def create_sync_task(
    config_id: str,
    request: SyncTaskRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建同步任务

    在集成配置下创建新的数据同步任务。
    """
    config = integration_store.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Integration config {config_id} not found")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="Integration config is not enabled")

    try:
        direction = SyncDirection(request.direction)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sync direction: {request.direction}",
        )

    task = SyncTask(
        id=f"sync-{uuid.uuid4().hex[:8]}",
        integration_id=config_id,
        workflow_id=request.workflow_id,
        direction=direction,
        status=SyncStatus.PENDING,
        source_data=request.source_data,
    )

    result = sync_task_store.create_task(task)

    return {
        "id": result.id,
        "integration_id": result.integration_id,
        "workflow_id": result.workflow_id,
        "direction": result.direction.value,
        "status": result.status.value,
        "progress": result.progress,
        "created_at": result.created_at.isoformat(),
    }


@router.get("/sync-tasks", response_model=dict, summary="列出同步任务")
async def list_sync_tasks(
    integration_id: Optional[str] = Query(default=None, description="集成配置ID过滤"),
    workflow_id: Optional[str] = Query(default=None, description="工作流ID过滤"),
    status: Optional[str] = Query(default=None, description="状态过滤"),
    user_id: str = Depends(get_current_user),
) -> dict:
    """列出同步任务"""
    status_enum = None
    if status:
        try:
            status_enum = SyncStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    tasks = sync_task_store.list_tasks(
        integration_id=integration_id,
        workflow_id=workflow_id,
        status=status_enum,
    )

    return {
        "tasks": [
            {
                "id": t.id,
                "integration_id": t.integration_id,
                "workflow_id": t.workflow_id,
                "direction": t.direction.value,
                "status": t.status.value,
                "progress": t.progress,
                "error_message": t.error_message,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.get("/sync-tasks/{task_id}", response_model=dict, summary="获取同步任务")
async def get_sync_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取同步任务详情"""
    task = sync_task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Sync task {task_id} not found")

    return {
        "id": task.id,
        "integration_id": task.integration_id,
        "workflow_id": task.workflow_id,
        "direction": task.direction.value,
        "status": task.status.value,
        "progress": task.progress,
        "source_data": task.source_data,
        "result_data": task.result_data,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.post("/sync-tasks/{task_id}/cancel", response_model=dict, summary="取消同步任务")
async def cancel_sync_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """取消正在执行或等待中的同步任务"""
    success = sync_task_store.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task {task_id} (not found or already completed)",
        )

    return {"message": f"Sync task {task_id} cancelled successfully"}
