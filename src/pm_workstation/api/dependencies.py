"""FastAPI 依赖注入

提供全局依赖项，如数据库连接、工作流管理器、当前用户等。
"""

from collections.abc import AsyncGenerator

from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from pm_workstation.auth.models import Base
from pm_workstation.llm.provider_store import LLMProviderStore
from pm_workstation.orchestrator.workflow_manager import WorkflowManager

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            "sqlite+aiosqlite:///./pm_workstation.db", echo=False
        )
    return _engine


def get_workflow_manager(request: Request) -> WorkflowManager:
    """获取工作流管理器实例"""
    return request.app.state.workflow_manager


def get_provider_store(request: Request) -> LLMProviderStore:
    """获取 LLM Provider 存储实例"""
    return request.app.state.provider_store


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session


async def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> str:
    """获取当前用户ID

    在实际生产环境中，这里应该验证 JWT token 并提取用户ID。
    目前使用请求头中的 X-User-ID 作为临时方案。
    测试环境中允许默认用户。
    """
    if not x_user_id:
        return "anonymous-test-user"
    return x_user_id
