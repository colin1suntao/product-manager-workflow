"""FastAPI 依赖注入

提供全局依赖项，如数据库连接、工作流管理器、当前用户等。
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from pm_workstation.orchestrator.workflow_manager import WorkflowManager


def get_workflow_manager(request: Request) -> WorkflowManager:
    """获取工作流管理器实例"""
    return request.app.state.workflow_manager


async def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> str:
    """获取当前用户ID

    在实际生产环境中，这里应该验证 JWT token 并提取用户ID。
    目前使用请求头中的 X-User-ID 作为临时方案。
    测试环境中允许默认用户。
    """
    if not x_user_id:
        return "anonymous-test-user"
    return x_user_id
