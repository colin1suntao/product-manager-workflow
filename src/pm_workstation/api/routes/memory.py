"""Memory API Routes - 记忆管理 API

提供 Agent Soul、用户偏好、记忆条目和反思记录的 REST API 接口。
"""

from fastapi import APIRouter, Depends, HTTPException

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.memory.memory_manager import MemoryManager
from pm_workstation.memory.memory_models import (
    AgentSoul,
    MemoryEntry,
    MemoryType,
    Reflection,
    UserPreference,
)
from pm_workstation.memory.reflection_engine import ReflectionEngine
from pm_workstation.memory.soul_manager import SoulManager

router = APIRouter(prefix="/memory", tags=["记忆管理"])

# 全局实例
_memory_manager = MemoryManager()
_soul_manager = SoulManager()
_reflection_engine = ReflectionEngine(_memory_manager)


def _get_memory_manager() -> MemoryManager:
    return _memory_manager


def _get_soul_manager() -> SoulManager:
    return _soul_manager


def _get_reflection_engine() -> ReflectionEngine:
    return _reflection_engine


# ============ Soul 管理 ============


@router.post("/soul", summary="创建 Agent Soul")
async def create_soul(
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """创建新的 Agent Soul

    Args:
        body: 包含 name, personality, values, behavior_rules, communication_style, expertise_areas
    """
    soul = AgentSoul(
        user_id=user_id,
        name=body.get("name", "自定义助手"),
        personality=body.get("personality", ""),
        values=body.get("values", []),
        behavior_rules=body.get("behavior_rules", []),
        communication_style=body.get("communication_style", ""),
        expertise_areas=body.get("expertise_areas", []),
    )

    created = await manager.create_soul(soul)

    return {
        "id": created.id,
        "name": created.name,
        "is_active": created.is_active,
        "created_at": created.created_at.isoformat(),
    }


@router.get("/soul", summary="获取当前激活的 Soul")
async def get_active_soul(
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """获取用户当前激活的 Agent Soul"""
    soul = await manager.get_active_soul(user_id)

    return {
        "id": soul.id,
        "name": soul.name,
        "personality": soul.personality,
        "values": soul.values,
        "behavior_rules": soul.behavior_rules,
        "communication_style": soul.communication_style,
        "expertise_areas": soul.expertise_areas,
        "is_active": soul.is_active,
        "created_at": soul.created_at.isoformat(),
        "updated_at": soul.updated_at.isoformat(),
    }


@router.put("/soul/{soul_id}", summary="更新 Soul")
async def update_soul(
    soul_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """更新 Agent Soul"""
    updated = await manager.update_soul(soul_id, body)

    if not updated:
        raise HTTPException(status_code=404, detail="Soul 不存在")

    return {
        "id": updated.id,
        "name": updated.name,
        "updated_at": updated.updated_at.isoformat(),
    }


@router.get("/soul/list", summary="列出所有 Soul")
async def list_souls(
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """列出用户的所有 Agent Soul"""
    souls = await manager.list_souls(user_id)

    return {
        "souls": [
            {
                "id": s.id,
                "name": s.name,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
            }
            for s in souls
        ],
        "total": len(souls),
    }


@router.post("/soul/{soul_id}/activate", summary="激活 Soul")
async def activate_soul(
    soul_id: str,
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """激活指定的 Agent Soul"""
    success = await manager.activate_soul(soul_id)

    if not success:
        raise HTTPException(status_code=404, detail="Soul 不存在")

    return {"message": "Soul 已激活"}


@router.delete("/soul/{soul_id}", summary="删除 Soul")
async def delete_soul(
    soul_id: str,
    user_id: str = Depends(get_current_user),
    manager: SoulManager = Depends(_get_soul_manager),
) -> dict:
    """删除 Agent Soul"""
    success = await manager.delete_soul(soul_id)

    if not success:
        raise HTTPException(status_code=400, detail="无法删除激活的 Soul 或 Soul 不存在")

    return {"message": "Soul 已删除"}


# ============ 偏好管理 ============


@router.post("/preferences", summary="创建用户偏好")
async def create_preference(
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """创建用户偏好"""
    memory = MemoryEntry(
        user_id=user_id,
        memory_type=MemoryType.PREFERENCE,
        content=body.get("value", ""),
        summary=f"{body.get('category', '')}: {body.get('key', '')}",
        tags=[body.get("category", "general")],
        importance=0.6,
        context={"category": body.get("category"), "key": body.get("key")},
    )

    created = await manager.add_memory(memory)

    return {
        "id": created.id,
        "category": body.get("category"),
        "key": body.get("key"),
        "value": body.get("value"),
        "created_at": created.created_at.isoformat(),
    }


@router.get("/preferences", summary="获取所有偏好")
async def list_preferences(
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """获取用户的所有偏好"""
    preferences = await manager.list_memories(
        user_id=user_id,
        memory_type=MemoryType.PREFERENCE,
    )

    return {
        "preferences": [
            {
                "id": p.id,
                "category": p.context.get("category", ""),
                "key": p.context.get("key", ""),
                "value": p.content,
                "created_at": p.created_at.isoformat(),
            }
            for p in preferences
        ],
        "total": len(preferences),
    }


@router.put("/preferences/{pref_id}", summary="更新偏好")
async def update_preference(
    pref_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """更新用户偏好"""
    updates = {}
    if "value" in body:
        updates["content"] = body["value"]

    updated = await manager.update_memory(pref_id, updates)

    if not updated:
        raise HTTPException(status_code=404, detail="偏好不存在")

    return {"message": "偏好已更新"}


@router.delete("/preferences/{pref_id}", summary="删除偏好")
async def delete_preference(
    pref_id: str,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """删除用户偏好"""
    success = await manager.delete_memory(pref_id)

    if not success:
        raise HTTPException(status_code=404, detail="偏好不存在")

    return {"message": "偏好已删除"}


# ============ 记忆管理 ============


@router.post("/entries", summary="创建记忆")
async def create_memory(
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """创建新的记忆条目"""
    memory = MemoryEntry(
        user_id=user_id,
        memory_type=MemoryType(body.get("memory_type", "experience")),
        content=body.get("content", ""),
        summary=body.get("summary", ""),
        tags=body.get("tags", []),
        importance=body.get("importance", 0.5),
        source=body.get("source", ""),
        context=body.get("context", {}),
    )

    created = await manager.add_memory(memory)

    return {
        "id": created.id,
        "memory_type": created.memory_type.value,
        "summary": created.summary,
        "created_at": created.created_at.isoformat(),
    }


@router.get("/entries", summary="列出记忆")
async def list_memories(
    memory_type: str = None,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """列出用户的记忆"""
    mt = MemoryType(memory_type) if memory_type else None
    memories = await manager.list_memories(user_id=user_id, memory_type=mt)

    return {
        "memories": [
            {
                "id": m.id,
                "memory_type": m.memory_type.value,
                "summary": m.summary,
                "content": m.content,
                "tags": m.tags,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": len(memories),
    }


@router.get("/entries/{memory_id}", summary="获取记忆详情")
async def get_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """获取记忆详情"""
    memory = await manager.get_memory(memory_id)

    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")

    return {
        "id": memory.id,
        "memory_type": memory.memory_type.value,
        "summary": memory.summary,
        "content": memory.content,
        "tags": memory.tags,
        "importance": memory.importance,
        "source": memory.source,
        "context": memory.context,
        "created_at": memory.created_at.isoformat(),
        "last_accessed": memory.last_accessed.isoformat(),
        "access_count": memory.access_count,
    }


@router.put("/entries/{memory_id}", summary="更新记忆")
async def update_memory(
    memory_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """更新记忆"""
    updated = await manager.update_memory(memory_id, body)

    if not updated:
        raise HTTPException(status_code=404, detail="记忆不存在")

    return {"message": "记忆已更新"}


@router.delete("/entries/{memory_id}", summary="删除记忆")
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """删除记忆"""
    success = await manager.delete_memory(memory_id)

    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")

    return {"message": "记忆已删除"}


@router.get("/search", summary="搜索记忆")
async def search_memories(
    q: str,
    memory_type: str = None,
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """搜索记忆"""
    mt = MemoryType(memory_type) if memory_type else None
    results = await manager.search_memories(user_id, q, memory_type=mt)

    return {
        "results": [
            {
                "id": r.memory.id,
                "memory_type": r.memory.memory_type.value,
                "summary": r.memory.summary,
                "relevance_score": r.relevance_score,
                "match_reason": r.match_reason,
            }
            for r in results
        ],
        "total": len(results),
    }


@router.get("/stats", summary="获取记忆统计")
async def get_stats(
    user_id: str = Depends(get_current_user),
    manager: MemoryManager = Depends(_get_memory_manager),
) -> dict:
    """获取用户记忆统计"""
    stats = await manager.get_stats(user_id)

    return {
        "total_memories": stats.total_memories,
        "by_type": stats.by_type,
        "top_tags": stats.top_tags,
    }


# ============ 反思管理 ============


@router.post("/reflect", summary="触发反思")
async def trigger_reflection(
    user_id: str = Depends(get_current_user),
    engine: ReflectionEngine = Depends(_get_reflection_engine),
) -> dict:
    """触发 Agent 反思"""
    reflection = await engine.execute_reflection(user_id)

    return {
        "id": reflection.id,
        "period_start": reflection.period_start.isoformat(),
        "period_end": reflection.period_end.isoformat(),
        "total_tasks": reflection.total_tasks,
        "successful_tasks": reflection.successful_tasks,
        "failed_tasks": reflection.failed_tasks,
        "key_learnings": reflection.key_learnings,
        "improvement_areas": reflection.improvement_areas,
        "action_items": reflection.action_items,
        "created_at": reflection.created_at.isoformat(),
    }


@router.get("/reflections", summary="获取反思记录")
async def list_reflections(
    user_id: str = Depends(get_current_user),
    engine: ReflectionEngine = Depends(_get_reflection_engine),
) -> dict:
    """获取用户的反思记录"""
    reflections = await engine.list_reflections(user_id)

    return {
        "reflections": [
            {
                "id": r.id,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "total_tasks": r.total_tasks,
                "successful_tasks": r.successful_tasks,
                "failed_tasks": r.failed_tasks,
                "key_learnings": r.key_learnings,
                "created_at": r.created_at.isoformat(),
            }
            for r in reflections
        ],
        "total": len(reflections),
    }


@router.get("/reflections/latest", summary="获取最新反思")
async def get_latest_reflection(
    user_id: str = Depends(get_current_user),
    engine: ReflectionEngine = Depends(_get_reflection_engine),
) -> dict:
    """获取用户最新的反思记录"""
    reflection = await engine.get_latest_reflection(user_id)

    if not reflection:
        return {"message": "暂无反思记录"}

    return {
        "id": reflection.id,
        "period_start": reflection.period_start.isoformat(),
        "period_end": reflection.period_end.isoformat(),
        "total_tasks": reflection.total_tasks,
        "successful_tasks": reflection.successful_tasks,
        "failed_tasks": reflection.failed_tasks,
        "key_learnings": reflection.key_learnings,
        "improvement_areas": reflection.improvement_areas,
        "action_items": reflection.action_items,
        "created_at": reflection.created_at.isoformat(),
    }
