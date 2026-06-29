"""三层记忆 API 路由

端点：
  - 短期记忆 (STM): 上下文查看
  - 工作记忆 (WM): 手动添加、加载、获取上下文
  - 长期记忆 (LTM): 完整 CRUD + 搜索 + 提升
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from pm_workstation.memory.layered_manager import LayeredMemoryManager, get_layered_memory_manager
from pm_workstation.memory.layered_models import (
    LongTermCategory,
    LongTermMemoryEntry,
    MemoryPriority,
    MemoryRetrievalQuery,
)

router = APIRouter(prefix="/memory/v2", tags=["三层记忆"])


def _get_manager() -> LayeredMemoryManager:
    return get_layered_memory_manager()


def _safe_enum(value: str, enum_cls):
    """安全解析枚举值，无效时抛出 HTTPException(422)"""
    try:
        return enum_cls(value)
    except ValueError:
        valid = [e.value for e in enum_cls]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid value '{value}' for {enum_cls.__name__}. Valid: {valid}",
        )


def _require_field(body: dict, field: str):
    """校验必填字段"""
    value = body.get(field, "")
    if not value or not str(value).strip():
        raise HTTPException(
            status_code=422,
            detail=f"Required field '{field}' is missing or empty",
        )
    return value


def _require_session(manager: LayeredMemoryManager):
    """校验会话已初始化，未初始化返回 409"""
    if not manager.stm or not manager.wm:
        raise HTTPException(
            status_code=409,
            detail="Session not initialized. Call POST /memory/v2/session/{session_id} first.",
        )


# ======================== 会话管理 ========================


@router.post("/session/{session_id}", summary="初始化会话记忆")
async def init_memory_session(
    session_id: str,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """为指定会话初始化三层记忆系统"""
    manager.init_session(session_id, user_id)
    return {
        "message": "会话记忆已初始化",
        "session_id": session_id,
        "user_id": user_id,
    }


@router.delete("/session/{session_id}", summary="结束会话")
async def end_memory_session(
    session_id: str,
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """结束会话并清理短期/工作记忆"""
    cleaned = manager.end_session(session_id=session_id)
    if not cleaned:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    return {"message": "会话记忆已清理", "session_id": session_id}


# ======================== 短期记忆 (STM) ========================


@router.get("/stm/context", summary="获取短期记忆上下文")
async def get_stm_context(
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """获取当前会话的短期记忆上下文"""
    _require_session(manager)
    return {
        "context": manager.get_stm_context(),
        "message_count": len(manager.stm.messages),
        "token_usage": manager.stm.current_tokens,
        "token_budget": manager.stm.token_budget,
    }


# ======================== 工作记忆 (WM) ========================


@router.post("/wm/load", summary="从长期记忆加载到工作记忆")
async def load_working_memory(
    body: dict,
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """根据当前任务从长期记忆加载关联条目到工作记忆"""
    _require_session(manager)

    results = manager.load_wm_from_ltm(
        task_description=body.get("task_description", ""),
        task_type=body.get("task_type", ""),
        task_id=body.get("task_id"),
        max_items=body.get("max_items", 10),
    )
    return {
        "loaded_count": len(results),
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "summary": e.summary,
                "category": e.category.value,
                "importance": e.importance,
            }
            for e in results
        ],
    }


@router.post("/wm/entries", summary="用户手动添加工作记忆")
async def add_working_memory(
    body: dict,
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """用户手动添加一条工作记忆

    请求体:
        - title (必填): 记忆标题
        - content (必填): 记忆内容
        - category (可选): project/session/user/knowledge/custom
        - tags (可选): 标签列表
        - priority (可选): critical/high/medium/low
        - importance (可选): 重要性 0-1
        - promote (可选): 是否同时保存为长期记忆
    """
    _require_session(manager)

    title = _require_field(body, "title")
    content = _require_field(body, "content")

    category = _safe_enum(body.get("category", "custom"), LongTermCategory)
    priority = _safe_enum(body.get("priority", "medium"), MemoryPriority)
    importance = body.get("importance", 0.7)
    tags = body.get("tags", [])

    entry = manager.add_wm_entry(
        title=title,
        content=content,
        category=category,
        tags=tags,
        priority=priority,
        importance=importance,
    )

    if body.get("promote", False):
        manager.promote_to_long_term(entry)

    return {
        "id": entry.id,
        "title": entry.title,
        "category": entry.category.value,
        "priority": entry.priority.value,
        "promoted": body.get("promote", False),
    }


@router.get("/wm/context", summary="获取工作记忆上下文")
async def get_wm_context(
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """获取当前任务的工作记忆上下文"""
    _require_session(manager)
    return {
        "context": manager.get_wm_context(),
        "task_description": manager.wm.task_description,
        "loaded_count": len(manager.wm.loaded_from_ltm),
        "manual_count": len(manager.wm.manual_entries),
    }


@router.delete("/wm/clear", summary="清除工作记忆")
async def clear_working_memory(
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """清除当前任务的工作记忆"""
    _require_session(manager)
    manager.clear_wm_task()
    return {"message": "工作记忆已清除"}


# ======================== 长期记忆 (LTM) CRUD ========================


@router.post("/ltm/entries", summary="创建长期记忆")
async def create_long_term_memory(
    body: dict,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """用户手动创建长期记忆条目

    请求体:
        - title (必填): 记忆标题
        - content (必填): 记忆内容
        - category (可选): project/session/user/knowledge/custom
        - tags (可选): 标签列表
        - priority (可选): critical/high/medium/low
        - importance (可选): 重要性 0-1
        - summary (可选): 自定义摘要
    """
    title = _require_field(body, "title")
    content = _require_field(body, "content")

    entry = LongTermMemoryEntry(
        user_id=user_id,
        title=title,
        content=content,
        summary=body.get("summary", content[:200]),
        category=_safe_enum(body.get("category", "custom"), LongTermCategory),

        priority=_safe_enum(body.get("priority", "medium"), MemoryPriority),
        importance=body.get("importance", 0.5),
        source="user_manual",
    )
    entry = manager.store_long_term(entry)
    return {
        "id": entry.id,
        "title": entry.title,
        "category": entry.category.value,
        "priority": entry.priority.value,
        "created_at": entry.created_at.isoformat(),
    }


@router.get("/ltm/entries", summary="列出长期记忆")
async def list_long_term_memories(
    user_id: str = Query(...),
    category: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """列出长期记忆条目（支持分页和筛选）"""
    cat = _safe_enum(category, LongTermCategory) if category else None
    pri = _safe_enum(priority, MemoryPriority) if priority else None
    tag_list = tags.split(",") if tags else None

    entries, total = manager.list_long_term(
        user_id=user_id,
        category=cat,
        tags=tag_list,
        priority=pri,
        page=page,
        page_size=page_size,
    )
    return {
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "summary": e.summary,
                "category": e.category.value,
                "tags": e.tags,
                "priority": e.priority.value,
                "importance": e.importance,
                "access_count": e.access_count,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/ltm/entries/{memory_id}", summary="获取长期记忆详情")
async def get_long_term_memory(
    memory_id: str,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """获取单条长期记忆详情"""
    entry = manager.get_long_term(user_id, memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "summary": entry.summary,
        "category": entry.category.value,
        "tags": entry.tags,
        "priority": entry.priority.value,
        "importance": entry.importance,
        "confidence": entry.confidence,
        "source": entry.source,
        "related_files": entry.related_files,
        "access_count": entry.access_count,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "last_accessed": entry.last_accessed.isoformat(),
    }


@router.put("/ltm/entries/{memory_id}", summary="更新长期记忆")
async def update_long_term_memory(
    memory_id: str,
    body: dict,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """用户手动更新长期记忆条目

    可更新字段: title, content, summary, tags, category, priority, importance, confidence
    """
    if "category" in body:
        body["category"] = _safe_enum(body["category"], LongTermCategory)
    if "priority" in body:
        body["priority"] = _safe_enum(body["priority"], MemoryPriority)

    entry = manager.update_long_term(memory_id, user_id=user_id, **body)
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {
        "id": entry.id,
        "title": entry.title,
        "updated_at": entry.updated_at.isoformat(),
    }


@router.delete("/ltm/entries/{memory_id}", summary="删除长期记忆")
async def delete_long_term_memory(
    memory_id: str,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """用户手动删除长期记忆条目"""
    success = manager.delete_long_term(user_id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"message": "记忆已删除", "id": memory_id}


@router.post("/ltm/search", summary="搜索长期记忆")
async def search_long_term_memories(
    body: dict,
    user_id: str = Query(...),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """搜索长期记忆（支持关键词、分类、标签、时间范围筛选）

    请求体:
        - keyword (可选): 搜索关键词
        - categories (可选): 分类列表
        - tags (可选): 标签列表
        - priority (可选): 优先级
        - min_importance (可选): 最低重要性
        - max_results (可选): 最大结果数
        - sort_by (可选): importance/recency/relevance
    """
    query = MemoryRetrievalQuery(
        user_id=user_id,
        keyword=body.get("keyword", ""),
        categories=(
            [_safe_enum(c, LongTermCategory) for c in body.get("categories", [])]
            if body.get("categories") else None,
        ),
        priority=(
            _safe_enum(body["priority"], MemoryPriority)
            if body.get("priority") else None
        ),
        min_importance=body.get("min_importance", 0.0),
        max_results=body.get("max_results", 20),
        sort_by=body.get("sort_by", "relevance"),
    )
    results = manager.search_long_term(query)
    return {
        "results": [
            {
                "id": e.id,
                "title": e.title,
                "summary": e.summary,
                "category": e.category.value,
                "tags": e.tags,
                "priority": e.priority.value,
                "importance": e.importance,
                "access_count": e.access_count,
                "created_at": e.created_at.isoformat(),
            }
            for e in results
        ],
        "total": len(results),
    }


@router.post("/ltm/promote/{memory_id}", summary="将工作记忆提升为长期记忆")
async def promote_to_long_term(
    memory_id: str,
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """将工作记忆条目提升为持久化的长期记忆"""
    _require_session(manager)

    target = None
    for e in manager.wm.manual_entries:
        if e.id == memory_id:
            target = e
            break
    if not target:
        for e in manager.wm.loaded_from_ltm:
            if e.id == memory_id:
                target = e
                break
    if not target:
        raise HTTPException(status_code=404, detail="工作记忆中未找到该条目")

    entry = manager.promote_to_long_term(target)
    return {
        "id": entry.id,
        "title": entry.title,
        "message": "已提升为长期记忆",
    }


# ======================== 组合注入上下文 ========================


@router.get("/context", summary="获取三层记忆完整注入上下文")
async def get_full_context(
    max_tokens: int = Query(default=4000),
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """获取组合三层记忆后的完整注入上下文"""
    _require_session(manager)
    return {
        "context": manager.get_full_injection_context(max_tokens=max_tokens),
    }


# ======================== 统计 ========================


@router.get("/stats", summary="获取记忆系统统计")
async def get_memory_stats(
    manager: LayeredMemoryManager = Depends(_get_manager),
) -> dict:
    """获取三层记忆系统的完整统计"""
    _require_session(manager)

    stats = manager.get_stats()
    return {
        "total_memories": stats.total_memories,
        "by_layer": stats.by_layer,
        "by_category": stats.by_category,
        "by_priority": stats.by_priority,
        "avg_importance": stats.avg_importance,
        "total_tokens_stm": stats.total_tokens_stm,
        "total_manual_entries": stats.total_manual_entries,
        "most_accessed": stats.most_accessed,
        "top_tags": stats.top_tags,
        "storage_size_bytes": stats.storage_size_bytes,
        "last_updated": stats.last_updated.isoformat() if stats.last_updated else None,
    }
