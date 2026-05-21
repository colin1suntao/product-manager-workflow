"""Sandbox API 路由

提供 Sandbox 执行环境的 REST API 和 SSE 流式 API。
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.sandbox.models import (
    CreateExecutionRequest,
    ExecutionContext,
    ExecutionStatus,
    ExecutionSummary,
    ToolInvocationRequest,
    ToolResult,
    StreamExecutionRequest,
    ToolCall,
    ToolDefinition,
)
from pm_workstation.sandbox.engine import SandboxEngine, get_sandbox_engine
from pm_workstation.sandbox.tool_manager import ToolManager, get_tool_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["Sandbox 执行环境"])


@router.post("/executions", summary="创建执行")
async def create_execution(
    body: CreateExecutionRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建 Sandbox 执行上下文
    
    Args:
        body: 创建请求
    
    Returns:
        dict: 执行上下文信息
    """
    engine = get_sandbox_engine()
    
    context = engine.create_execution(
        task_params=body.task_params,
        timeout=body.timeout,
        resource_limits=body.resource_limits,
        session_id=body.session_id,
        workflow_id=body.workflow_id,
    )
    
    return {
        "execution_id": context.execution_id,
        "workspace_path": context.workspace_path,
        "status": context.status.value,
        "timeout": context.timeout,
        "created_at": context.created_at.isoformat(),
    }


@router.post("/executions/{execution_id}/tools/{tool_name}", summary="调用工具")
async def invoke_tool(
    execution_id: str,
    tool_name: str,
    body: ToolInvocationRequest,
    user_id: str = Depends(get_current_user),
) -> ToolResult:
    """在执行上下文中调用工具
    
    Args:
        execution_id: 执行 ID
        tool_name: 工具名称
        body: 工具调用请求
    
    Returns:
        ToolResult: 工具执行结果
    """
    engine = get_sandbox_engine()
    
    context = engine.get_execution_status(execution_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    if context.status not in [ExecutionStatus.CREATED, ExecutionStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Execution is not active: {context.status.value}"
        )
    
    result = await engine.invoke_tool(
        context=context,
        tool_name=tool_name,
        params=body.params,
    )
    
    return result


@router.post("/executions/{execution_id}/stream", summary="流式执行")
async def stream_execution(
    execution_id: str,
    body: StreamExecutionRequest,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    """流式执行多个工具调用
    
    Args:
        execution_id: 执行 ID
        body: 流式执行请求
    
    Returns:
        StreamingResponse: SSE 流式响应
    """
    engine = get_sandbox_engine()
    
    context = engine.get_execution_status(execution_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    if context.status not in [ExecutionStatus.CREATED, ExecutionStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Execution is not active: {context.status.value}"
        )
    
    async def event_generator():
        for event in await engine.execute_streaming(context, body.tool_calls):
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/executions/{execution_id}/finalize", summary="结束执行")
async def finalize_execution(
    execution_id: str,
    user_id: str = Depends(get_current_user),
) -> ExecutionSummary:
    """结束执行，收集产物
    
    Args:
        execution_id: 执行 ID
    
    Returns:
        ExecutionSummary: 执行摘要
    """
    engine = get_sandbox_engine()
    
    context = engine.get_execution_status(execution_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    summary = engine.finalize_execution(context)
    
    return summary


@router.get("/executions/{execution_id}", summary="获取执行状态")
async def get_execution_status(
    execution_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取执行状态和日志
    
    Args:
        execution_id: 执行 ID
    
    Returns:
        dict: 执行状态
    """
    engine = get_sandbox_engine()
    
    context = engine.get_execution_status(execution_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return {
        "execution_id": context.execution_id,
        "status": context.status.value,
        "workspace_path": context.workspace_path,
        "tool_results_count": len(context.tool_results),
        "artifacts_count": len(context.artifacts),
        "created_at": context.created_at.isoformat(),
        "error_message": context.error_message,
    }


@router.get("/executions/{execution_id}/artifacts", summary="获取产物")
async def get_execution_artifacts(
    execution_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取执行产物列表
    
    Args:
        execution_id: 执行 ID
    
    Returns:
        dict: 产物列表
    """
    engine = get_sandbox_engine()
    
    context = engine.get_execution_status(execution_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return {
        "execution_id": execution_id,
        "artifacts": [
            {
                "file_path": a.file_path,
                "file_name": a.file_name,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "created_at": a.created_at.isoformat(),
            }
            for a in context.artifacts
        ],
        "total": len(context.artifacts),
    }


@router.post("/executions/{execution_id}/cancel", summary="取消执行")
async def cancel_execution(
    execution_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """取消执行
    
    Args:
        execution_id: 执行 ID
    
    Returns:
        dict: 取消结果
    """
    engine = get_sandbox_engine()
    
    success = engine.cancel_execution(execution_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return {
        "execution_id": execution_id,
        "status": "cancelled",
        "message": "Execution cancelled successfully",
    }


@router.delete("/executions/{execution_id}", summary="清理工作区")
async def cleanup_execution(
    execution_id: str,
    preserve_artifacts: bool = True,
    user_id: str = Depends(get_current_user),
) -> dict:
    """清理执行工作区
    
    Args:
        execution_id: 执行 ID
        preserve_artifacts: 是否保留产物
    """
    engine = get_sandbox_engine()
    
    success = engine.cleanup_workspace(execution_id, preserve_artifacts)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return {
        "execution_id": execution_id,
        "message": "Workspace cleaned up",
        "preserve_artifacts": preserve_artifacts,
    }


@router.get("/tools", summary="获取工具列表")
async def list_tools() -> dict:
    """获取所有可用工具定义"""
    tool_manager = get_tool_manager()
    
    tools = tool_manager.list_tools()
    
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "returns": t.returns,
                "timeout": t.timeout,
                "category": t.category.value,
                "security_level": t.security_level.value,
            }
            for t in tools
        ],
        "total": len(tools),
    }


@router.get("/tools/{tool_name}", summary="获取工具详情")
async def get_tool_detail(
    tool_name: str,
) -> ToolDefinition:
    """获取工具详细定义"""
    tool_manager = get_tool_manager()
    
    tool = tool_manager.get_tool(tool_name)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    return tool


@router.post("/tools/{tool_name}/validate", summary="验证工具参数")
async def validate_tool_params(
    tool_name: str,
    body: dict,
) -> dict:
    """验证工具参数
    
    Args:
        tool_name: 工具名称
        body: 参数
    """
    tool_manager = get_tool_manager()
    
    tool = tool_manager.get_tool(tool_name)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    valid, error = tool_manager.validate_params(tool, body)
    
    return {
        "valid": valid,
        "error": error,
    }