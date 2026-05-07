"""FastAPI 应用配置"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse

from pm_workstation.llm.provider_store import LLMProviderStore
from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter
from pm_workstation.model_router.base import LLMConfig
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.model_router.openai_adapter import OpenAIAdapter
from pm_workstation.orchestrator.workflow_manager import WorkflowManager

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")


def _build_llm_handler(provider_config) -> Optional[FallbackHandler]:
    """从 LLM Provider 配置构建 llm_handler

    Args:
        provider_config: LLMProviderConfig 对象

    Returns:
        FallbackHandler 实例，如果配置无效则返回 None
    """
    if not provider_config or not provider_config.is_active:
        return None

    config = LLMConfig(
        model=provider_config.default_model,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
        temperature=0.7,
        max_tokens=16384,
    )

    if provider_config.provider_type.value == "openai":
        primary = OpenAIAdapter(config)
    elif provider_config.provider_type.value == "anthropic":
        primary = AnthropicAdapter(config)
    else:
        # CUSTOM 类型默认使用 OpenAI 兼容接口
        primary = OpenAIAdapter(config)

    # 包装为 FallbackHandler（即使没有备选模型，也保持统一接口）
    return FallbackHandler(primary_model=primary, fallback_models=[])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时初始化
    app.state.provider_store = LLMProviderStore()

    # 尝试构建 LLM handler
    llm_handler = None
    try:
        default_config = await app.state.provider_store.get_default_config()
        if default_config:
            llm_handler = _build_llm_handler(default_config)
    except Exception:
        pass

    app.state.workflow_manager = WorkflowManager(llm_handler=llm_handler)
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

    # 静态文件服务 - 产物
    @app.get("/artifacts/{workflow_id}/{filename}")
    async def serve_artifact(workflow_id: str, filename: str):
        filepath = os.path.join(ARTIFACTS_DIR, workflow_id, filename)
        if not os.path.exists(filepath):
            return {"error": "Artifact not found"}
        media_type = "text/html" if filename.endswith(".html") else "text/markdown" if filename.endswith(".md") else "application/json"
        return FileResponse(filepath, media_type=media_type)

    return app
