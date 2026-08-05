"""FastAPI 应用配置"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pm_workstation.api.routes.artifact_routes import router as artifact_routes_router

# 路由导入
from pm_workstation.api.routes.auth import router as auth_router
from pm_workstation.api.routes.channels import router as channels_router
from pm_workstation.api.routes.chat import router as chat_router
from pm_workstation.api.routes.component_library import router as component_library_router
from pm_workstation.api.routes.components import router as components_router
from pm_workstation.api.routes.evolution import router as evolution_router
from pm_workstation.api.routes.integrations import router as integrations_router
from pm_workstation.api.routes.knowledge_base import router as knowledge_base_router
from pm_workstation.api.routes.layered_memory import router as layered_memory_router
from pm_workstation.api.routes.llm import router as llm_router
from pm_workstation.api.routes.market_research import router as market_research_router
from pm_workstation.api.routes.memory import router as memory_router
from pm_workstation.api.routes.persistent_memory import router as persistent_memory_router
from pm_workstation.api.routes.skills import router as skills_router
from pm_workstation.api.routes.streaming_chat import router as streaming_chat_router
from pm_workstation.api.routes.token_usage import router as token_usage_router
from pm_workstation.api.routes.workflow_routes import router as workflow_routes_router
from pm_workstation.api.routes.workflows import router as workflows_router
from pm_workstation.llm.provider_store import LLMProviderStore
from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter
from pm_workstation.model_router.base import LLMConfig
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.model_router.openai_adapter import OpenAIAdapter
from pm_workstation.orchestrator.workflow_manager import WorkflowManager
from pm_workstation.sandbox.api.routes import router as sandbox_router

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")

# 前端静态文件目录 (Next.js 静态导出)
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "out"

# 全局 provider_store 引用，供其他模块访问
app_state_provider_store = None


def _build_llm_handler(provider_config, model_override: str | None = None) -> FallbackHandler | None:
    """从 LLM Provider 配置构建 llm_handler

    Args:
        provider_config: LLMProviderConfig 对象
        model_override: 可选的模型名称覆盖

    Returns:
        FallbackHandler 实例，如果配置无效则返回 None
    """
    if not provider_config or not provider_config.is_active:
        return None

    model = model_override or provider_config.default_model

    config = LLMConfig(
        model=model,
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


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    global app_state_provider_store

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        global app_state_provider_store

        from pm_workstation.api.dependencies import init_db_tables

        # 初始化数据库表（仅启动时一次）
        try:
            await init_db_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")

        # 初始化 LLM Provider Store
        provider_store = LLMProviderStore()
        app_state_provider_store = provider_store
        # 设置到 app.state 供依赖注入使用
        app.state.provider_store = provider_store

        # 尝试构建默认 LLM handler
        llm_handler = None
        try:
            default_config = await provider_store.get_default_config()
            if default_config:
                llm_handler = _build_llm_handler(default_config)
        except Exception as e:
            logger.error(f"Failed to initialize LLM handler: {e}")

        # 初始化 Workflow Manager（带 LLM handler 和 provider_store）
        workflow_manager = WorkflowManager(llm_handler=llm_handler, provider_store=provider_store)
        app.state.llm_handler = llm_handler
        app.state.workflow_manager = workflow_manager

        yield

    app = FastAPI(
        title="PM Workstation API",
        description="Product Manager Workstation Backend API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 配置 - 允许所有来源（开发环境）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(auth_router, prefix="/api/v1", tags=["认证"])
    app.include_router(llm_router, prefix="/api/v1", tags=["LLM 配置"])
    app.include_router(workflows_router, prefix="/api/v1", tags=["工作流"])
    app.include_router(components_router, prefix="/api/v1", tags=["组件库"])
    app.include_router(component_library_router, prefix="/api/v1", tags=["组件模板库"])
    app.include_router(integrations_router, prefix="/api/v1", tags=["集成配置"])
    app.include_router(knowledge_base_router, prefix="/api/v1", tags=["知识库"])
    app.include_router(skills_router, prefix="/api/v1", tags=["PM Skills"])
    app.include_router(market_research_router, prefix="/api/v1", tags=["市场调研"])
    app.include_router(chat_router, prefix="/api/v1", tags=["会话交互"])
    app.include_router(streaming_chat_router, prefix="/api/v1", tags=["会话交互-流式"])
    app.include_router(workflow_routes_router, prefix="/api/v1", tags=["工作流编排"])
    app.include_router(artifact_routes_router, prefix="/api/v1", tags=["产物管理"])
    app.include_router(channels_router, prefix="/api/v1", tags=["渠道管理"])
    app.include_router(memory_router, prefix="/api/v1", tags=["记忆管理"])
    app.include_router(layered_memory_router, prefix="/api/v1", tags=["三层记忆"])
    app.include_router(persistent_memory_router, prefix="/api/v1", tags=["持久化记忆"])
    app.include_router(token_usage_router, prefix="/api/v1", tags=["模型用量"])
    app.include_router(sandbox_router, prefix="/api/v1", tags=["Sandbox 执行环境"])
    app.include_router(evolution_router, prefix="/api/v1", tags=["自我进化"])

    # 健康检查
    @app.get("/health", tags=["健康检查"])
    async def health_check() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    # 静态文件服务 - 产物（防止路径穿越）
    @app.get("/artifacts/{workflow_id}/{filename}")
    async def serve_artifact(workflow_id: str, filename: str):
        safe_workflow = os.path.normpath(workflow_id)
        safe_filename = os.path.normpath(filename)
        if safe_workflow.startswith("..") or safe_workflow.startswith("/"):
            return {"error": "Invalid workflow_id"}
        if safe_filename.startswith("..") or safe_filename.startswith("/"):
            return {"error": "Invalid filename"}
        filepath = os.path.join(ARTIFACTS_DIR, safe_workflow, safe_filename)
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(os.path.realpath(ARTIFACTS_DIR)):
            return {"error": "Path traversal denied"}
        if not os.path.exists(filepath):
            return {"error": "Artifact not found"}
        media_type = "text/html" if filename.endswith(".html") else "text/markdown" if filename.endswith(".md") else "application/json"
        return FileResponse(filepath, media_type=media_type)

    # 静态文件服务 - Chat 产物（防止路径穿越）
    @app.get("/artifacts/chat/{filename}")
    async def serve_chat_artifact(filename: str):
        safe_filename = os.path.normpath(filename)
        if safe_filename.startswith("..") or safe_filename.startswith("/"):
            return {"error": "Invalid filename"}
        filepath = os.path.join(ARTIFACTS_DIR, "chat", safe_filename)
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(os.path.realpath(ARTIFACTS_DIR)):
            return {"error": "Path traversal denied"}
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

        # Catch-all 路由处理前端页面（防止路径穿越）
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def serve_frontend(request: Request, path: str):
            safe_path = os.path.normpath(path)
            if safe_path.startswith(".."):
                return HTMLResponse(content="<h1>Forbidden</h1>", status_code=403)
            file_path = FRONTEND_DIR / safe_path
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(FRONTEND_DIR.resolve())):
                return HTMLResponse(content="<h1>Forbidden</h1>", status_code=403)
            if resolved.is_file():
                return FileResponse(str(resolved))

            if path and not path.endswith((".js", ".css", ".ico", ".png", ".jpg", ".svg")):
                page_path = FRONTEND_DIR / safe_path / "index.html"
                if page_path.is_file():
                    return FileResponse(str(page_path))

            # 默认返回 index.html (SPA 路由)
            index_path = FRONTEND_DIR / "index.html"
            if index_path.is_file():
                return FileResponse(str(index_path))

            return HTMLResponse(content="<h1>Frontend not built</h1>", status_code=404)

    return app


app = create_app()
