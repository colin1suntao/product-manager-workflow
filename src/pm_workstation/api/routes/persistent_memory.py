"""Persistent Memory API Routes - 持久化记忆 API

提供项目级、会话级、用户偏好持久化的 REST API。
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.memory import (
    MemoryInjectionConfig,
    PersistentMemoryManager,
    ProjectMemoryType,
    get_persistent_memory_manager,
)

router = APIRouter(prefix="/persistent-memory", tags=["持久化记忆"])


def _get_manager() -> PersistentMemoryManager:
    return get_persistent_memory_manager()


# ============ 用户偏好 ============


@router.post("/preferences", summary="保存用户偏好")
async def save_preference(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """保存用户偏好到持久化存储

    Body:
        - key: 偏好键
        - value: 偏好值
        - category: 分类（可选）
        - confidence: 置信度（可选，默认 0.9）
    """
    success = await manager.save_user_preference(
        user_id=user_id,
        key=body.get("key", ""),
        value=body.get("value", ""),
        category=body.get("category"),
        confidence=body.get("confidence", 0.9),
    )

    return {"success": success, "key": body.get("key", "")}


@router.get("/preferences", summary="获取用户偏好")
async def get_preferences(
    category: str | None = Query(None, description="偏好分类"),
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """获取用户偏好列表"""
    from pm_workstation.memory.persistent_store import get_persistent_memory_store
    store = get_persistent_memory_store()

    prefs = await store.get_user_preferences(user_id, category)

    return {
        "preferences": [
            {
                "id": p.id,
                "key": p.key,
                "value": p.value,
                "category": p.category,
                "confidence": p.confidence,
                "created_at": p.created_at.isoformat(),
            }
            for p in prefs
        ],
        "total": len(prefs),
    }


# ============ 项目记忆 ============


@router.post("/projects/{project_id}/memories", summary="保存项目记忆")
async def save_project_memory(
    project_id: str,
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """保存项目记忆

    Body:
        - title: 标题
        - content: 内容
        - memory_type: 记忆类型（knowledge, decision, pattern, mistake, feedback）
        - importance: 重要性（0-1，默认 0.7）
    """
    memory_type = ProjectMemoryType(body.get("memory_type", "decision"))

    memory = await manager.save_project_memory(
        project_id=project_id,
        user_id=user_id,
        title=body.get("title", ""),
        content=body.get("content", ""),
        memory_type=memory_type,
        importance=body.get("importance", 0.7),
    )

    return {
        "id": memory.id,
        "project_id": memory.project_id,
        "title": memory.title,
        "memory_type": memory.memory_type.value,
    }


@router.get("/projects/{project_id}/memories", summary="获取项目记忆")
async def get_project_memories(
    project_id: str,
    memory_type: str | None = Query(None, description="记忆类型"),
    limit: int = Query(50, description="最大数量"),
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """获取项目记忆列表"""
    from pm_workstation.memory.persistent_store import get_persistent_memory_store
    store = get_persistent_memory_store()

    memories = await store.get_project_memories(project_id, memory_type)

    memories = sorted(memories, key=lambda m: m.importance, reverse=True)[:limit]

    return {
        "memories": [
            {
                "id": m.id,
                "title": m.title,
                "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                "memory_type": m.memory_type.value,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": len(memories),
    }


# ============ 会话记忆 ============


@router.post("/sessions/{session_id}/memories", summary="保存会话记忆")
async def save_session_memory(
    session_id: str,
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """保存会话记忆

    Body:
        - content: 内容
        - entities: 实体列表（可选）
        - importance: 重要性（0-1，默认 0.5）
    """
    memory = await manager.save_session_memory(
        session_id=session_id,
        user_id=user_id,
        content=body.get("content", ""),
        entities=body.get("entities", []),
        importance=body.get("importance", 0.5),
    )

    return {
        "id": memory.id,
        "session_id": memory.session_id,
    }


@router.get("/sessions/{session_id}/memories", summary="获取会话记忆")
async def get_session_memories(
    session_id: str,
    recent_hours: int = Query(24, description="最近小时数"),
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """获取会话记忆列表"""
    from pm_workstation.memory.persistent_store import get_persistent_memory_store
    store = get_persistent_memory_store()

    memories = await store.get_session_memories(session_id)

    from datetime import datetime, timedelta
    threshold = datetime.now() - timedelta(hours=recent_hours)
    memories = [m for m in memories if m.created_at >= threshold]

    return {
        "memories": [
            {
                "id": m.id,
                "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "entities": m.entities,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": len(memories),
    }


# ============ 记忆检索 ============


@router.post("/retrieve", summary="检索上下文记忆")
async def retrieve_memories(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """检索相关记忆用于注入上下文

    Body:
        - session_id: 会话 ID
        - project_id: 项目 ID（可选）
        - context_keywords: 上下文关键词（可选）
        - max_memories: 最大记忆数量（可选，默认 20）
    """
    config = MemoryInjectionConfig(
        max_memories=body.get("max_memories", 20),
        max_tokens=body.get("max_tokens", 2000),
    )

    memories = await manager.get_context_memories(
        user_id=user_id,
        session_id=body.get("session_id", ""),
        project_id=body.get("project_id"),
        context_keywords=body.get("context_keywords", []),
        config=config,
    )

    return {
        "memories": [
            {
                "id": m.memory.id,
                "level": m.memory.level.value,
                "type": m.memory.memory_type,
                "content": m.memory.content[:150] + "..." if len(m.memory.content) > 150 else m.memory.content,
                "relevance": m.relevance_score,
                "reason": m.match_reason,
            }
            for m in memories
        ],
        "total": len(memories),
    }


@router.get("/search", summary="关键词搜索记忆")
async def search_memories(
    q: str = Query(..., description="搜索关键词"),
    project_id: str | None = Query(None, description="项目 ID"),
    limit: int = Query(20, description="最大结果数"),
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """按关键词搜索记忆"""
    keywords = q.split()

    results = await manager.retriever.search_by_keywords(
        keywords=keywords,
        user_id=user_id,
        project_id=project_id,
        limit=limit,
    )

    return {
        "results": [
            {
                "id": r.memory.id,
                "level": r.memory.level.value,
                "type": r.memory.memory_type,
                "summary": r.memory.summary,
                "relevance": r.relevance_score,
                "matched_keywords": r.matched_keywords,
            }
            for r in results
        ],
        "total": len(results),
    }


# ============ 记忆处理（自动提取） ============


@router.post("/process/workflow", summary="处理工作流结果")
async def process_workflow(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """从工作流执行结果自动提取记忆

    Body:
        - workflow_execution: 工作流执行结果（包含 steps_results, artifacts 等）
        - project_id: 项目 ID（可选）
        - session_id: 会话 ID（可选）
    """
    memories = await manager.process_workflow_result(
        workflow_execution=body.get("workflow_execution", {}),
        user_id=user_id,
        project_id=body.get("project_id"),
        session_id=body.get("session_id"),
    )

    return {
        "extracted": len(memories),
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type,
                "summary": m.summary,
            }
            for m in memories
        ],
    }


@router.post("/process/sandbox", summary="处理 Sandbox 执行结果")
async def process_sandbox(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """从 Sandbox 执行结果自动提取记忆

    Body:
        - sandbox_execution: Sandbox 执行结果
        - project_id: 项目 ID（可选）
        - session_id: 会话 ID（可选）
    """
    memories = await manager.process_sandbox_result(
        sandbox_execution=body.get("sandbox_execution", {}),
        user_id=user_id,
        project_id=body.get("project_id"),
        session_id=body.get("session_id"),
    )

    return {
        "extracted": len(memories),
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type,
                "summary": m.summary,
            }
            for m in memories
        ],
    }


@router.post("/process/chat", summary="处理对话消息")
async def process_chat(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """从对话消息自动提取记忆

    Body:
        - message: 对话消息（包含 role, content 等）
        - project_id: 项目 ID（可选）
        - session_id: 会话 ID（可选）
    """
    memories = await manager.process_chat_message(
        message=body.get("message", {}),
        user_id=user_id,
        project_id=body.get("project_id"),
        session_id=body.get("session_id"),
    )

    return {
        "extracted": len(memories),
    }


@router.post("/process/feedback", summary="处理用户反馈")
async def process_feedback(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """从用户反馈自动提取记忆

    Body:
        - feedback: 用户反馈（包含 rating, comment 等）
        - project_id: 项目 ID（可选）
        - session_id: 会话 ID（可选）
    """
    memories = await manager.process_user_feedback(
        feedback=body.get("feedback", {}),
        user_id=user_id,
        project_id=body.get("project_id"),
        session_id=body.get("session_id"),
    )

    return {
        "extracted": len(memories),
    }


# ============ 维护操作 ============


@router.post("/archive", summary="归档旧记忆")
async def archive_memories(
    body: dict[str, Any],
    user_id: str = Depends(get_current_user),
    manager: PersistentMemoryManager = Depends(_get_manager),
) -> dict[str, Any]:
    """归档超过指定天数的记忆

    Body:
        - days_threshold: 天数阈值（默认 30）
    """
    count = await manager.archive_old_memories(
        user_id=user_id,
        days_threshold=body.get("days_threshold", 30),
    )

    return {
        "archived": count,
    }
