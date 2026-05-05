"""FastAPI 应用配置"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from pm_workstation.orchestrator.workflow_manager import WorkflowManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时初始化
    app.state.workflow_manager = WorkflowManager()
    yield
    # 关闭时清理
    pass


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    from pm_workstation.api.routes.auth import router as auth_router
    from pm_workstation.api.routes.components import router as components_router
    from pm_workstation.api.routes.integrations import router as integrations_router
    from pm_workstation.api.routes.llm import router as llm_router
    from pm_workstation.api.routes.workflows import router as workflows_router

    app = FastAPI(
        title="PM Workstation API",
        description="产品经理多Agent协作工作站 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 注册路由
    app.include_router(auth_router, prefix="/api/v1", tags=["认证"])
    app.include_router(llm_router, prefix="/api/v1", tags=["LLM 配置"])
    app.include_router(workflows_router, prefix="/api/v1", tags=["工作流"])
    app.include_router(components_router, prefix="/api/v1", tags=["组件库"])
    app.include_router(integrations_router, prefix="/api/v1", tags=["集成配置"])

    # 健康检查
    @app.get("/health", tags=["健康检查"])
    async def health_check() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    return app
