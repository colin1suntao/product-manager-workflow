"""LLM Provider API 路由

提供 LLM Provider 配置管理的 REST API 接口。
"""

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.api.schemas import (
    LLMProviderConfigCreate,
    LLMProviderConfigResponse,
    LLMProviderConfigUpdate,
    LLMProviderListResponse,
    LLMTestRequest,
    LLMTestResponse,
)
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.llm.factory import LLMFactory
from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType
from pm_workstation.llm.provider_store import LLMProviderStore

router = APIRouter(prefix="/llm", tags=["LLM 配置"])

# 全局 Provider 存储
_provider_store = LLMProviderStore()


def get_provider_store() -> LLMProviderStore:
    """获取 Provider 存储实例"""
    return _provider_store


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
