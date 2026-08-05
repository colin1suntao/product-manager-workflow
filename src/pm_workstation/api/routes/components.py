"""组件库 API 路由

提供组件管理相关的 REST API 接口。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentSearchRequest,
    ComponentStatus,
    ComponentUploadRequest,
)
from pm_workstation.storage.component_store_memory import InMemoryComponentStore

router = APIRouter(prefix="/components")

# 全局组件存储（实际生产应使用数据库）
_component_store = InMemoryComponentStore()


class ComponentResponse:
    """组件响应模型"""

    @staticmethod
    def from_component(component: Component) -> dict:
        """将 Component 转换为字典响应"""
        return {
            "id": component.id,
            "name": component.name,
            "version": component.current_version if isinstance(component.current_version, str) else "1.0.0",
            "category": component.category.value if isinstance(component.category, ComponentCategory) else component.category,
            "description": component.description,
            "tags": component.tags,
            "status": component.status.value if isinstance(component.status, ComponentStatus) else component.status,
            "created_at": component.created_at.isoformat() if component.created_at else None,
            "updated_at": component.updated_at.isoformat() if component.updated_at else None,
        }


@router.post("", response_model=dict, summary="上传组件")
async def upload_component(
    request: ComponentUploadRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """上传新组件

    创建一个新的组件并保存到组件库中。
    """
    category = ComponentCategory(request.category) if isinstance(request.category, str) else request.category

    component = Component(
        id=f"comp-{uuid.uuid4().hex[:8]}",
        name=request.name,
        category=category,
        description=request.description,
        tags=request.tags or [],
        current_version=request.version or "1.0.0",
    )

    result = await _component_store.create_component(component)
    return ComponentResponse.from_component(result)


@router.get("", response_model=dict, summary="搜索组件")
async def search_components(
    q: str | None = Query(default=None, description="搜索关键词"),
    category: str | None = Query(default=None, description="组件分类"),
    tag: str | None = Query(default=None, description="标签过滤"),
    status: str | None = Query(default=None, description="状态过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_current_user),
) -> dict:
    """搜索组件

    支持按关键词、分类、标签、状态搜索组件。
    """
    cat_enum = None
    if category:
        try:
            cat_enum = ComponentCategory(category)
        except ValueError:
            valid = [e.value for e in ComponentCategory]
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category '{category}'. Valid: {valid}",
            )

    stat_enum = None
    if status:
        try:
            stat_enum = ComponentStatus(status)
        except ValueError:
            valid = [e.value for e in ComponentStatus]
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Valid: {valid}",
            )

    search_request = ComponentSearchRequest(
        query=q or "",
        category=cat_enum,
        tags=[tag] if tag else [],
        status=stat_enum,
    )

    results = await _component_store.search(search_request)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    page_items = results[start:end]

    return {
        "components": [ComponentResponse.from_component(r.component) for r in page_items],
        "total": len(results),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{component_id}", response_model=dict, summary="获取组件")
async def get_component(
    component_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取组件详情

    返回指定组件的完整信息。
    """
    component = await _component_store.get_component(component_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Component {component_id} not found")

    return ComponentResponse.from_component(component)


@router.delete("/{component_id}", response_model=dict, summary="删除组件")
async def delete_component(
    component_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """删除组件

    从组件库中删除指定组件。
    """
    component = await _component_store.get_component(component_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Component {component_id} not found")

    success = await _component_store.delete_component(component_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete component")

    return {"message": f"Component {component_id} deleted successfully"}
