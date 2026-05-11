"""Chat API Routes - 会话交互 API

提供会话管理、消息发送和任务执行的 REST API 接口。
"""

import time
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
    ToolCall,
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
    return _build_coordinator_from_store(request.app.state.provider_store)


def _build_coordinator_from_store(provider_store, provider_id: str | None = None, model_name: str | None = None) -> CoordinatorChatAgent:
    """根据指定 provider 和模型构建 Coordinator"""
    import asyncio
    from pm_workstation.api.app import _build_llm_handler

    llm_handler = None
    try:
        if provider_id:
            config = asyncio.run(provider_store.get_config(provider_id))
        else:
            config = asyncio.run(provider_store.get_default_config())
        if config:
            llm_handler = _build_llm_handler(config, model_override=model_name)
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
        body: 包含 content, task_mode（可选）, selected_skills（可选）, provider_id（可选）, model_name（可选）的请求体
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
    provider_id = body.get("provider_id")
    model_name = body.get("model_name")

    # 如果指定了 provider_id 或 model_name，使用对应的 coordinator
    if provider_id or model_name:
        from pm_workstation.api.app import app_state_provider_store
        coordinator = _build_coordinator_from_store(
            app_state_provider_store, provider_id=provider_id, model_name=model_name
        )

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

    # 计算当前上下文长度（所有消息的字符数总和）
    all_messages = await manager.get_messages(session_id)
    context_length = sum(len(m.content) for m in all_messages)
    context_limit = 128000

    # 处理消息（记录耗时）
    start_time = time.monotonic()
    response = await coordinator.process_message(
        message=content,
        context=context,
        selected_skills=selected_skills,
        task_mode=task_mode,
        user_id=user_id,
    )
    thinking_time_ms = int((time.monotonic() - start_time) * 1000)

    # 统计工具/技能调用
    tool_calls = []
    if selected_skills:
        for skill in selected_skills:
            tool_calls.append(ToolCall(
                tool_name=skill,
                tool_type="skill",
                status="used",
                description=f"使用了 PM Skill: {skill}",
            ))
    if task_mode:
        tool_calls.append(ToolCall(
            tool_name=task_mode.value,
            tool_type="function",
            status="used",
            description=f"执行了 {task_mode.value} 任务",
        ))

    # 估算 token 用量（粗略：1 token ≈ 4 字符）
    prompt_chars = len(content) + sum(len(m.content) for m in context)
    completion_chars = len(response.message)
    token_usage = {
        "prompt_tokens": max(1, prompt_chars // 4),
        "completion_tokens": max(1, completion_chars // 4),
        "total_tokens": max(1, (prompt_chars + completion_chars) // 4),
    }

    # 添加 Agent 响应
    assistant_message = ChatMessage(
        id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=response.message,
        task_mode=task_mode,
        task_status=TaskStatus.COMPLETED if response.task_results else None,
        thinking_time_ms=thinking_time_ms,
        token_usage=token_usage,
        tool_calls=tool_calls,
        context_length=context_length,
        context_limit=context_limit,
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
            "thinking_time_ms": assistant_message.thinking_time_ms,
            "token_usage": assistant_message.token_usage,
            "tool_calls": [
                {"tool_name": t.tool_name, "tool_type": t.tool_type, "description": t.description}
                for t in assistant_message.tool_calls
            ],
            "context_length": assistant_message.context_length,
            "context_limit": assistant_message.context_limit,
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
                "thinking_time_ms": m.thinking_time_ms,
                "token_usage": m.token_usage,
                "tool_calls": [
                    {"tool_name": t.tool_name, "tool_type": t.tool_type, "description": t.description}
                    for t in m.tool_calls
                ],
                "context_length": m.context_length,
                "context_limit": m.context_limit,
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


@router.post("/sessions/{session_id}/compress", summary="压缩上下文")
async def compress_context(
    session_id: str,
    user_id: str = Depends(get_current_user),
    manager: ChatManager = Depends(_get_chat_manager),
) -> dict:
    """压缩会话上下文，保留最近的 N 条消息，将旧消息摘要"""
    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    messages = await manager.get_messages(session_id)

    # 保留最近的 20 条消息，移除更早的消息
    keep_count = 20
    if len(messages) > keep_count:
        total = len(messages)
        # 收集需要删除的消息 ID（先收集，避免迭代时列表被修改）
        ids_to_remove = [m.id for m in messages[:-keep_count]]

        # 逐个删除
        for msg_id in ids_to_remove:
            await manager._delete_message(session_id, msg_id)

        # 添加一条系统消息说明上下文已压缩
        compressed_msg = ChatMessage(
            id=uuid.uuid4().hex,
            session_id=session_id,
            role="system",
            content=f"上下文已压缩。移除了 {len(ids_to_remove)} 条旧消息，保留了最近 {keep_count} 条消息。",
        )
        await manager.add_message(session_id, compressed_msg)

        return {
            "message": f"上下文已压缩",
            "removed_count": len(ids_to_remove),
            "remaining_count": keep_count + 1,
        }

    return {
        "message": "上下文长度正常，无需压缩",
        "removed_count": 0,
        "remaining_count": len(messages),
    }
