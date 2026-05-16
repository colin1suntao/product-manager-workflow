"""知识库 API - 产品文档模板和原型组件模板管理"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.knowledge_base.models import Template, TemplateType, TEMPLATE_TYPE_LABELS
from pm_workstation.knowledge_base.store import TemplateStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-base", tags=["知识库"])

_store = TemplateStore()


def get_store() -> TemplateStore:
    return _store


@router.get("/templates", summary="获取模板列表")
async def list_templates(
    type: str | None = None,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    type_filter = None
    if type:
        try:
            type_filter = TemplateType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的模板类型: {type}")

    templates = await store.list_all(type_filter)
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.type.value,
                "type_label": TEMPLATE_TYPE_LABELS.get(t.type, t.type.value),
                "tags": t.tags,
                "content_preview": t.content[:200] + "..." if len(t.content) > 200 else t.content,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in templates
        ],
        "total": len(templates),
    }


@router.get("/templates/{template_id}", summary="获取模板详情")
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    template = await store.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "type": template.type.value,
        "type_label": TEMPLATE_TYPE_LABELS.get(template.type, template.type.value),
        "content": template.content,
        "tags": template.tags,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


@router.post("/templates", summary="创建模板")
async def create_template(
    body: dict,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    type_str = body.get("type", "").strip()
    try:
        template_type = TemplateType(type_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的模板类型: {type_str}")

    template = Template(
        name=name,
        description=body.get("description", ""),
        type=template_type,
        content=body.get("content", ""),
        tags=body.get("tags", []),
    )

    result = await store.create(template)
    return {
        "id": result.id,
        "name": result.name,
        "type": result.type.value,
        "message": f"模板 '{result.name}' 创建成功",
    }


@router.put("/templates/{template_id}", summary="更新模板")
async def update_template(
    template_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    existing = await store.get(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="模板不存在")

    updates = {}
    for field in ("name", "description", "content", "tags"):
        if field in body:
            updates[field] = body[field]

    result = await store.update(template_id, updates)
    return {
        "id": result.id,
        "name": result.name,
        "message": "模板已更新",
    }


@router.delete("/templates/{template_id}", summary="删除模板")
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    deleted = await store.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "模板已删除"}


@router.get("/types", summary="获取模板类型列表")
async def get_template_types(
    user_id: str = Depends(get_current_user),
) -> dict:
    return {
        "types": [
            {"value": t.value, "label": TEMPLATE_TYPE_LABELS[t]}
            for t in TemplateType
        ]
    }