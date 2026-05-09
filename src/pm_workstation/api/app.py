"""FastAPI 应用配置"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pm_workstation.llm.provider_store import LLMProviderStore
from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter
from pm_workstation.model_router.base import LLMConfig
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.model_router.openai_adapter import OpenAIAdapter
from pm_workstation.orchestrator.workflow_manager import WorkflowManager

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")

# 前端静态文件目录 (Next.js 静态导出)
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "out"


def _build_llm_handler(provider_config) -> FallbackHandler | None:
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

    # 如果没有配置，尝试从环境变量创建默认配置
    configs = await app.state.provider_store.list_configs()
    if not configs:
        _try_create_default_provider(app.state.provider_store)

    # 尝试构建 LLM handler
    llm_handler = None
    try:
        default_config = await app.state.provider_store.get_default_config()
        if default_config:
            llm_handler = _build_llm_handler(default_config)
    except Exception:
        pass

    app.state.llm_handler = llm_handler
    app.state.workflow_manager = WorkflowManager(llm_handler=llm_handler)
    yield
    # 关闭时清理
    pass


def _try_create_default_provider(store) -> None:
    """尝试从环境变量创建默认 LLM Provider 配置"""
    import asyncio
    from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType

    # 检查环境变量
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MCAI_LLM_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("MCAI_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("MCAI_LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        return

    # 判断 provider 类型
    provider_type = LLMProviderType.OPENAI
    if "anthropic" in base_url.lower():
        provider_type = LLMProviderType.ANTHROPIC

    config = LLMProviderConfig(
        id="default-env",
        name="Default (from env)",
        provider_type=provider_type,
        api_key=api_key,
        base_url=base_url,
        default_model=model,
        is_active=True,
        is_default=True,
    )

    try:
        asyncio.get_event_loop().run_until_complete(store.create_config(config))
    except Exception:
        pass


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    from pm_workstation.api.routes.auth import router as auth_router
    from pm_workstation.api.routes.chat import router as chat_router
    from pm_workstation.api.routes.components import router as components_router
    from pm_workstation.api.routes.integrations import router as integrations_router
    from pm_workstation.api.routes.llm import router as llm_router
    from pm_workstation.api.routes.market_research import router as market_research_router
    from pm_workstation.api.routes.skills import router as skills_router
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
    app.include_router(skills_router, prefix="/api/v1", tags=["PM Skills"])
    app.include_router(market_research_router, prefix="/api/v1", tags=["市场调研"])
    app.include_router(chat_router, prefix="/api/v1", tags=["会话交互"])

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

    # 静态文件服务 - Chat 产物
    @app.get("/artifacts/chat/{filename}")
    async def serve_chat_artifact(filename: str):
        filepath = os.path.join(ARTIFACTS_DIR, "chat", filename)
        if not os.path.exists(filepath):
            return {"error": "Artifact not found"}
        media_type = "text/html" if filename.endswith(".html") else "text/markdown" if filename.endswith(".md") else "application/json"
        return FileResponse(filepath, media_type=media_type)

    # 前端静态文件服务
    if FRONTEND_DIR.exists():
        # 挂载 Next.js 静态资源
        next_static_dir = FRONTEND_DIR / "_next"
        if next_static_dir.exists():
            app.mount("/_next", StaticFiles(directory=str(next_static_dir)), name="next_static")
        
        # Catch-all 路由处理前端页面
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def serve_frontend(request: Request, path: str):
            # 尝试查找精确匹配的文件
            file_path = FRONTEND_DIR / path
            if file_path.is_file():
                return FileResponse(str(file_path))
            
            # 尝试查找 index.html
            if path and not path.endswith((".js", ".css", ".ico", ".png", ".jpg", ".svg")):
                page_path = FRONTEND_DIR / path / "index.html"
                if page_path.is_file():
                    return FileResponse(str(page_path))
            
            # 默认返回 index.html (SPA 路由)
            index_path = FRONTEND_DIR / "index.html"
            if index_path.is_file():
                return FileResponse(str(index_path))
            
            return HTMLResponse(content="<h1>Frontend not built</h1>", status_code=404)

    return app
