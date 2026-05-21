"""LLM Provider API 路由

提供 LLM Provider 配置管理的 REST API 接口。
"""

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.api.dependencies import get_provider_store
from pm_workstation.api.schemas import (
    LLMModelListRequest,
    LLMModelListResponse,
    LLMProviderConfigCreate,
    LLMProviderConfigResponse,
    LLMProviderConfigUpdate,
    LLMProviderListResponse,
    LLMQuickTestRequest,
    LLMTestRequest,
    LLMTestResponse,
)
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.llm.factory import LLMFactory
from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType
from pm_workstation.llm.provider_store import LLMProviderStore

router = APIRouter(prefix="/llm", tags=["LLM 配置"])


@router.get("/providers", response_model=LLMProviderListResponse, summary="列出 LLM Provider")
async def list_providers(
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> LLMProviderListResponse:
    """列出所有 LLM Provider 配置"""
    configs = await store.list_configs()
    return LLMProviderListResponse(
        providers=[c.to_display_dict() for c in configs],
        total=len(configs),
    )


@router.post("/providers", response_model=LLMProviderConfigResponse, summary="创建 LLM Provider")
async def create_provider(
    request: LLMProviderConfigCreate,
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> LLMProviderConfigResponse:
    """创建新的 LLM Provider 配置"""
    # 如果是第一个配置，自动设置为默认
    existing = await store.list_configs()
    is_default = request.is_default or len(existing) == 0

    config = LLMProviderConfig(
        name=request.name,
        provider_type=LLMProviderType(request.provider_type),
        api_key=request.api_key,
        base_url=request.base_url,
        default_model=request.default_model,
        available_models=request.available_models,
        is_active=request.is_active,
        is_default=is_default,
    )

    created = await store.create_config(config)
    return LLMProviderConfigResponse(**created.to_display_dict())


@router.put("/providers/{provider_id}", response_model=LLMProviderConfigResponse, summary="更新 LLM Provider")
async def update_provider(
    provider_id: str,
    request: LLMProviderConfigUpdate,
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> LLMProviderConfigResponse:
    """更新 LLM Provider 配置"""
    updates = request.model_dump(exclude_unset=True)
    updated = await store.update_config(provider_id, updates)

    if not updated:
        raise HTTPException(status_code=404, detail="LLM Provider 不存在")

    return LLMProviderConfigResponse(**updated.to_display_dict())


@router.delete("/providers/{provider_id}", summary="删除 LLM Provider")
async def delete_provider(
    provider_id: str,
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> dict:
    """删除 LLM Provider 配置"""
    deleted = await store.delete_config(provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="LLM Provider 不存在")

    return {"message": "LLM Provider 已删除"}


@router.post("/providers/{provider_id}/test", response_model=LLMTestResponse, summary="测试 LLM 连通性")
async def test_provider(
    provider_id: str,
    request: LLMTestRequest,
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> LLMTestResponse:
    """测试 LLM Provider 连通性"""
    config = await store.get_config(provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM Provider 不存在")

    try:
        adapter = LLMFactory.create_adapter(config)
        import time

        from pm_workstation.model_router.base import LLMMessage

        start_time = time.time()
        response = await adapter.chat(
            messages=[LLMMessage(role="user", content="Say 'OK' in one word")],
        )
        elapsed = round((time.time() - start_time) * 1000)

        return LLMTestResponse(
            success=True,
            response_time_ms=elapsed,
            model=response.model,
            message="连通性测试成功",
        )
    except Exception as e:
        return LLMTestResponse(
            success=False,
            response_time_ms=0,
            model=config.default_model,
            message=f"测试失败: {str(e)}",
        )


@router.post("/providers/{provider_id}/set-default", summary="设置默认 LLM Provider")
async def set_default_provider(
    provider_id: str,
    user_id: str = Depends(get_current_user),
    store: LLMProviderStore = Depends(get_provider_store),
) -> dict:
    """设置默认 LLM Provider"""
    success = await store.set_default(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="LLM Provider 不存在")

    return {"message": "默认 LLM Provider 已更新"}


@router.post("/test-connection", response_model=LLMTestResponse, summary="快速测试连通性")
async def quick_test_connection(
    request: LLMQuickTestRequest,
    user_id: str = Depends(get_current_user),
) -> LLMTestResponse:
    """快速测试 LLM 连通性（无需保存配置）"""
    import asyncio
    import time

    from pm_workstation.model_router.base import LLMConfig, LLMMessage

    config = LLMConfig(
        model=request.default_model or "gpt-4o",
        api_key=request.api_key,
        base_url=request.base_url,
    )

    try:
        if request.provider_type == "openai" or request.provider_type == "custom":
            from pm_workstation.model_router.openai_adapter import OpenAIAdapter

            adapter = OpenAIAdapter(config=config)
        elif request.provider_type == "anthropic":
            from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter

            adapter = AnthropicAdapter(config=config)
        else:
            raise HTTPException(status_code=400, detail="不支持的提供商类型")

        start_time = time.time()
        response = await asyncio.wait_for(
            adapter.chat(
                messages=[LLMMessage(role="user", content="Say 'OK' in one word")],
            ),
            timeout=60.0,
        )
        elapsed = round((time.time() - start_time) * 1000)

        return LLMTestResponse(
            success=True,
            response_time_ms=elapsed,
            model=response.model,
            message="连通性测试成功",
        )
    except HTTPException:
        raise
    except TimeoutError:
        return LLMTestResponse(
            success=False,
            response_time_ms=0,
            model=request.default_model or "",
            message="测试超时：请检查网络连接和代理设置",
        )
    except Exception as e:
        error_msg = str(e)
        # 提供更友好的错误信息
        if "Connection" in error_msg or "connect" in error_msg.lower():
            error_msg = f"连接失败：{error_msg}\n请检查：1) 网络是否可达 2) 是否需要配置代理 3) Base URL 是否正确"
        elif "401" in error_msg or "Unauthorized" in error_msg:
            error_msg = "API Key 无效或已过期"
        elif "403" in error_msg or "Forbidden" in error_msg:
            error_msg = "API Key 权限不足"
        elif "404" in error_msg or "Not Found" in error_msg:
            error_msg = f"模型不存在或 Base URL 错误：{error_msg}"

        return LLMTestResponse(
            success=False,
            response_time_ms=0,
            model=request.default_model or "",
            message=f"测试失败: {error_msg}",
        )


@router.post("/list-models", response_model=LLMModelListResponse, summary="获取可用模型列表")
async def list_models(
    request: LLMModelListRequest,
    user_id: str = Depends(get_current_user),
) -> LLMModelListResponse:
    """获取 LLM 提供商可用模型列表"""
    from pm_workstation.model_router.base import LLMConfig

    config = LLMConfig(
        model="gpt-4o",
        api_key=request.api_key,
        base_url=request.base_url,
    )

    try:
        if request.provider_type == "openai" or request.provider_type == "custom":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=30.0,
            )
            models_resp = await client.models.list()
            models = [{"id": m.id, "object": m.object} for m in models_resp.data]
        elif request.provider_type == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=30.0,
            )
            models = [
                {"id": "claude-sonnet-4-20250514", "object": "model"},
                {"id": "claude-3-5-sonnet-20241022", "object": "model"},
                {"id": "claude-3-opus-20240229", "object": "model"},
                {"id": "claude-3-haiku-20240307", "object": "model"},
            ]
        else:
            raise HTTPException(status_code=400, detail="不支持的提供商类型")

        return LLMModelListResponse(
            models=models,
            total=len(models),
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "ConnectTimeout" in error_msg or "Connection" in error_msg:
            error_msg = "连接超时：无法连接到 LLM 服务提供商。\n请检查：\n1. 网络连接是否正常\n2. Base URL 是否正确\n3. 是否需要配置代理"
        elif "404" in error_msg or "Not Found" in error_msg:
            error_msg = "404 错误：模型列表接口不存在。\n请检查 Base URL 是否正确，确保包含完整路径（如 https://api.openai.com/v1）"
        elif "401" in error_msg or "Unauthorized" in error_msg:
            error_msg = "401 错误：API Key 无效或已过期"
        elif "403" in error_msg or "Forbidden" in error_msg:
            error_msg = "403 错误：API Key 权限不足"
        elif "timeout" in error_msg.lower():
            error_msg = "请求超时：服务响应时间过长，请稍后重试"

        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {error_msg}")
