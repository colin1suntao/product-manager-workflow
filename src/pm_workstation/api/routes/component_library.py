"""组件库 API - 原型组件模板管理"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.component_library.models import ComponentTemplate
from pm_workstation.component_library.store import ComponentTemplateStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/component-library", tags=["组件库"])

_store = ComponentTemplateStore()


def get_store() -> ComponentTemplateStore:
    return _store


@router.get("/templates", summary="获取组件模板列表")
async def list_templates(
    user_id: str = Depends(get_current_user),
    store: ComponentTemplateStore = Depends(get_store),
) -> dict:
    templates = await store.list_all()
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "tags": t.tags,
                "content_preview": t.content[:200] + "..." if len(t.content) > 200 else t.content,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in templates
        ],
        "total": len(templates),
    }


@router.get("/templates/{template_id}", summary="获取组件模板详情")
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: ComponentTemplateStore = Depends(get_store),
) -> dict:
    template = await store.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="组件模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "content": template.content,
        "tags": template.tags,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


@router.post("/templates", summary="创建组件模板")
async def create_template(
    body: dict,
    user_id: str = Depends(get_current_user),
    store: ComponentTemplateStore = Depends(get_store),
) -> dict:
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    template = ComponentTemplate(
        name=name,
        description=body.get("description", ""),
        content=body.get("content", ""),
        tags=body.get("tags", []),
    )

    result = await store.create(template)
    return {
        "id": result.id,
        "name": result.name,
        "message": f"组件模板 '{result.name}' 创建成功",
    }


@router.put("/templates/{template_id}", summary="更新组件模板")
async def update_template(
    template_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    store: ComponentTemplateStore = Depends(get_store),
) -> dict:
    existing = await store.get(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="组件模板不存在")

    updates = {}
    for field in ("name", "description", "content", "tags"):
        if field in body:
            updates[field] = body[field]

    result = await store.update(template_id, updates)
    return {
        "id": result.id,
        "name": result.name,
        "message": "组件模板已更新",
    }


@router.delete("/templates/{template_id}", summary="删除组件模板")
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: ComponentTemplateStore = Depends(get_store),
) -> dict:
    deleted = await store.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="组件模板不存在")
    return {"message": "组件模板已删除"}
