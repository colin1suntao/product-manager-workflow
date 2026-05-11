"""Chat API Routes - 会话交互 API

提供会话管理、消息发送和任务执行的 REST API 接口。
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from pm_workstation.agents.coordinator_chat import CoordinatorChatAgent
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.chat.chat_manager import ChatManager
from pm_workstation.chat.chat_models import (
    ChatMessage,
    ChatSession,
    CoordinatorResponse,
    TaskMode,
    TaskResult,
    TaskStatus,
)
from pm_workstation.chat.task_router import TaskRouter
from pm_workstation.memory.memory_manager import MemoryManager
from pm_workstation.memory.memory_retriever import MemoryRetriever
from pm_workstation.memory.soul_manager import SoulManager

router = APIRouter(prefix="/chat", tags=["会话交互"])

# 全局实例
_chat_manager = ChatManager()
_memory_manager = MemoryManager()
_soul_manager = SoulManager()
_memory_retriever = MemoryRetriever(_memory_manager)


def _get_chat_manager() -> ChatManager:
    """获取会话管理器"""
    return _chat_manager


def _get_coordinator(request: Request) -> CoordinatorChatAgent:
    """获取主 Agent"""
    # 动态获取最新的 LLM handler
    provider_store = request.app.state.provider_store
    llm_handler = None
    
    try:
        import asyncio
        default_config = asyncio.run(provider_store.get_default_config())
        if default_config:
            from pm_workstation.api.app import _build_llm_handler
            llm_handler = _build_llm_handler(default_config)
    except Exception:
        pass
    
    task_router = TaskRouter(llm_handler=llm_handler)
    return CoordinatorChatAgent(
        llm_handler=llm_handler,
        task_router=task_router,
        memory_retriever=_memory_retriever,
        soul_manager=_soul_manager,
    )


# ============ 会话管理 ============


@router.post("/sessions", summary="创建新会话")
async def create_session(
    body: dict,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """创建新的会话

    Args:
        body: 包含 title（可选）的请求体
    """
    title = body.get("title")
    session = await manager.create_session(user_id, title)

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.get("/sessions", summary="获取会话列表")
async def list_sessions(
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """获取用户的会话列表"""
    sessions = await manager.list_sessions(user_id)

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}", summary="获取会话详情")
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """获取会话详情"""
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """删除会话"""
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权删除此会话")

    await manager.delete_session(session_id)

    return {"message": "会话已删除"}


# ============ 消息管理 ============


@router.post("/sessions/{session_id}/messages", summary="发送消息")
async def send_message(
    session_id: str,
    body: dict,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
    coordinator: CoordinatorChatAgent = Depends(_get_coordinator),
) -> dict:
    """发送消息并获取 Agent 响应

    Args:
        body: 包含 content, task_mode（可选）, selected_skills（可选）的请求体
    """
    # 验证会话存在
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    task_mode_str = body.get("task_mode")
    task_mode = TaskMode(task_mode_str) if task_mode_str else None
    selected_skills = body.get("selected_skills", [])

    # 添加用户消息
    user_message = ChatMessage(
        id=uuid.uuid4().hex,
        session_id=session_id,
        role="user",
        content=content,
        task_mode=task_mode,
    )
    await manager.add_message(session_id, user_message)

    # 获取上下文
    context = await manager.get_context_messages(session_id, limit=10)

    # 处理消息（后台执行）
    response = await coordinator.process_message(
        message=content,
        context=context,
        selected_skills=selected_skills,
        task_mode=task_mode,
        user_id=user_id,
    )

    # 添加 Agent 响应
    assistant_message = ChatMessage(
        id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=response.message,
        task_mode=task_mode,
        task_status=TaskStatus.COMPLETED if response.task_results else None,
    )

    # 如果有任务结果，附加到消息
    if response.task_results:
        result = response.task_results[0]
        assistant_message.task_id = result.task_id
        assistant_message.task_status = result.status
        assistant_message.task_result = result
        assistant_message.artifacts = result.artifacts

    await manager.add_message(session_id, assistant_message)

    return {
        "user_message": {
            "id": user_message.id,
            "content": user_message.content,
            "created_at": user_message.created_at.isoformat(),
        },
        "assistant_message": {
            "id": assistant_message.id,
            "content": assistant_message.content,
            "task_mode": assistant_message.task_mode.value if assistant_message.task_mode else None,
            "task_status": assistant_message.task_status.value if assistant_message.task_status else None,
            "artifacts": [
                {"name": a.name, "url": a.url, "type": a.type}
                for a in assistant_message.artifacts
            ],
            "created_at": assistant_message.created_at.isoformat(),
        },
    }


@router.get("/sessions/{session_id}/messages", summary="获取消息历史")
async def get_messages(
    session_id: str,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """获取会话的消息历史"""
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    messages = await manager.get_messages(session_id)

    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "task_mode": m.task_mode.value if m.task_mode else None,
                "task_status": m.task_status.value if m.task_status else None,
                "artifacts": [
                    {"name": a.name, "url": a.url, "type": a.type}
                    for a in m.artifacts
                ],
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": len(messages),
    }


# ============ 任务管理 ============


@router.get("/sessions/{session_id}/tasks/{task_id}", summary="获取任务状态")
async def get_task_status(
    session_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """获取任务执行状态"""
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    # 从消息中查找任务
    messages = await manager.get_messages(session_id)
    for msg in messages:
        if msg.task_id == task_id:
            return {
                "task_id": task_id,
                "status": msg.task_status.value if msg.task_status else "unknown",
                "result": msg.task_result.model_dump() if msg.task_result else None,
            }

    raise HTTPException(status_code=404, detail="任务不存在")
