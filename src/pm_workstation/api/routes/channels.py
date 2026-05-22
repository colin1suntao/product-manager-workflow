"""渠道管理 API - 渠道配置、Webhook 接收、AI 会话对接"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.channels.channel_store import ChannelStore
from pm_workstation.channels.models import ChannelConfig, ChannelStatus, ChannelType, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["渠道管理"])

_channel_store = ChannelStore()


def _get_store() -> ChannelStore:
    return _channel_store


def _build_adapter(config: ChannelConfig):
    if config.channel_type == ChannelType.FEISHU:
        from pm_workstation.channels.feishu_adapter import FeishuAdapter
        return FeishuAdapter(config)
    elif config.channel_type == ChannelType.WECHAT:
        from pm_workstation.channels.wechat_adapter import WeChatAdapter
        return WeChatAdapter(config)
    raise ValueError(f"Unknown channel type: {config.channel_type}")


async def _process_incoming_message(incoming: IncomingMessage) -> str:
    from pm_workstation.agents.coordinator_chat import CoordinatorChatAgent
    from pm_workstation.api.app import app_state_provider_store
    from pm_workstation.api.routes.chat import _build_coordinator_from_store
    from pm_workstation.chat.chat_manager import ChatManager
    from pm_workstation.chat.chat_models import ChatMessage
    from pm_workstation.chat.task_router import TaskRouter
    from pm_workstation.llm.token_usage import TokenUsageStore

    chat_manager = ChatManager()
    token_usage_store = TokenUsageStore()

    session_key = f"{incoming.channel_type.value}:{incoming.chat_id or incoming.user_id}"

    sessions = await chat_manager.list_sessions("system")
    session = None
    for s in sessions:
        if s.metadata.get("channel_session_key") == session_key:
            session = s
            break

    if not session:
        title = f"[{incoming.channel_type.value}] {incoming.user_name or incoming.user_id}"
        session = await chat_manager.create_session("system", title)
        session.metadata["channel_session_key"] = session_key
        session.metadata["channel_id"] = incoming.channel_id
        session.metadata["channel_type"] = incoming.channel_type.value

    import time

    user_message = ChatMessage(
        id=uuid.uuid4().hex,
        session_id=session.id,
        role="user",
        content=incoming.content,
    )
    await chat_manager.add_message(session.id, user_message)

    context = await chat_manager.get_context_messages(session.id, limit=10)

    try:
        coordinator = await _build_coordinator_from_store(app_state_provider_store)
    except Exception:
        coordinator = CoordinatorChatAgent(llm_handler=None, task_router=TaskRouter(llm_handler=None))

    start_time = time.monotonic()
    try:
        import asyncio
        response = await asyncio.wait_for(
            coordinator.process_message(
                message=incoming.content,
                context=context,
                user_id="system",
            ),
            timeout=60.0,
        )
    except Exception as e:
        logger.error(f"[ChannelMessage] AI processing failed: {e}")
        response_text = "抱歉，处理消息时出现错误，请稍后重试。"
        token_usage_store.record(model_id="", total_tokens=0, source=f"channel_{incoming.channel_type.value}")
        return response_text

    thinking_time_ms = int((time.monotonic() - start_time) * 1000)

    token_usage = {
        "prompt_tokens": max(1, len(incoming.content) // 4),
        "completion_tokens": max(1, len(response.message) // 4),
        "total_tokens": max(1, (len(incoming.content) + len(response.message)) // 4),
    }

    token_usage_store.record(
        model_id=response.model_id,
        prompt_tokens=token_usage["prompt_tokens"],
        completion_tokens=token_usage["completion_tokens"],
        total_tokens=token_usage["total_tokens"],
        source=f"channel_{incoming.channel_type.value}",
    )

    assistant_message = ChatMessage(
        id=uuid.uuid4().hex,
        session_id=session.id,
        role="assistant",
        content=response.message,
        thinking_time_ms=thinking_time_ms,
        thinking_process=response.thinking_process,
        model_id=response.model_id,
        token_usage=token_usage,
    )
    await chat_manager.add_message(session.id, assistant_message)

    await _channel_store.increment_message_count(incoming.channel_id)

    return response.message


# ============ 渠道配置管理 ============


@router.get("", summary="获取渠道列表")
async def list_channels(
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    configs = await store.list_all()
    return {
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "channel_type": c.channel_type.value,
                "status": c.status.value,
                "config": {
                    k: ("***" if k in ("app_secret", "secret", "token", "encoding_aes_key") and v else v)
                    for k, v in c.config.items()
                },
                "webhook_url": f"/api/v1/channels/{c.id}/webhook",
                "message_count": c.message_count,
                "last_error": c.last_error,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in configs
        ],
        "total": len(configs),
    }


@router.post("", summary="创建渠道")
async def create_channel(
    body: dict,
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    name = body.get("name", "").strip()
    channel_type_str = body.get("channel_type", "").strip()
    config_data = body.get("config", {})

    if not name:
        raise HTTPException(status_code=400, detail="渠道名称不能为空")
    try:
        channel_type = ChannelType(channel_type_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的渠道类型: {channel_type_str}")

    channel_config = ChannelConfig(
        name=name,
        channel_type=channel_type,
        config=config_data,
    )

    adapter = _build_adapter(channel_config)
    valid, err = adapter.validate_config()
    if not valid:
        channel_config.status = ChannelStatus.ERROR
        channel_config.last_error = err
    else:
        channel_config.status = ChannelStatus.ACTIVE

    result = await store.create(channel_config)

    return {
        "id": result.id,
        "name": result.name,
        "channel_type": result.channel_type.value,
        "status": result.status.value,
        "webhook_url": f"/api/v1/channels/{result.id}/webhook",
        "last_error": result.last_error,
    }


@router.get("/{channel_id}", summary="获取渠道详情")
async def get_channel(
    channel_id: str,
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    config = await store.get(channel_id)
    if not config:
        raise HTTPException(status_code=404, detail="渠道不存在")

    return {
        "id": config.id,
        "name": config.name,
        "channel_type": config.channel_type.value,
        "status": config.status.value,
        "config": config.config,
        "webhook_url": f"/api/v1/channels/{config.id}/webhook",
        "message_count": config.message_count,
        "last_error": config.last_error,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }


@router.put("/{channel_id}", summary="更新渠道配置")
async def update_channel(
    channel_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    config = await store.get(channel_id)
    if not config:
        raise HTTPException(status_code=404, detail="渠道不存在")

    updates = {}
    if "name" in body:
        updates["name"] = body["name"]
    if "config" in body:
        merged = {**config.config, **body["config"]}
        updates["config"] = merged
    if "status" in body:
        try:
            updates["status"] = ChannelStatus(body["status"])
        except ValueError:
            pass

    result = await store.update(channel_id, updates)

    if result and "config" in updates:
        adapter = _build_adapter(result)
        valid, err = adapter.validate_config()
        if not valid:
            await store.update(channel_id, {"status": ChannelStatus.ERROR, "last_error": err})
        else:
            await store.update(channel_id, {"status": ChannelStatus.ACTIVE, "last_error": None})

    config = await store.get(channel_id)
    return {
        "id": config.id,
        "name": config.name,
        "channel_type": config.channel_type.value,
        "status": config.status.value,
        "webhook_url": f"/api/v1/channels/{config.id}/webhook",
        "last_error": config.last_error,
    }


@router.delete("/{channel_id}", summary="删除渠道")
async def delete_channel(
    channel_id: str,
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    deleted = await store.delete(channel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"message": "渠道已删除"}


@router.post("/{channel_id}/test", summary="测试渠道连接")
async def test_channel(
    channel_id: str,
    user_id: str = Depends(get_current_user),
    store: ChannelStore = Depends(_get_store),
) -> dict:
    config = await store.get(channel_id)
    if not config:
        raise HTTPException(status_code=404, detail="渠道不存在")

    adapter = _build_adapter(config)
    valid, err = adapter.validate_config()

    connection_valid = False
    connection_msg = ""

    if valid and hasattr(adapter, "test_connection"):
        connection_valid, connection_msg = await adapter.test_connection()

    webhook_url = adapter.get_webhook_url_hint()

    if valid and connection_valid:
        await store.update(channel_id, {"status": ChannelStatus.ACTIVE, "last_error": None})
        final_msg = connection_msg or "配置验证通过"
    else:
        error_detail = err or connection_msg or "配置验证失败"
        await store.update(channel_id, {"status": ChannelStatus.ERROR, "last_error": error_detail})
        final_msg = error_detail

    return {
        "valid": valid and connection_valid,
        "config_valid": valid,
        "connection_valid": connection_valid,
        "error": final_msg if not (valid and connection_valid) else None,
        "webhook_url": webhook_url,
        "message": final_msg,
    }


# ============ Webhook 接收 ============


@router.post("/{channel_id}/webhook", summary="接收渠道 Webhook 回调")
async def channel_webhook(
    channel_id: str,
    request: Request,
    store: ChannelStore = Depends(_get_store),
) -> dict:
    config = await store.get(channel_id)
    if not config:
        raise HTTPException(status_code=404, detail="渠道不存在")

    if config.status != ChannelStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="渠道未激活")

    adapter = _build_adapter(config)

    try:
        body = await request.json()
    except Exception:
        body = {}

    headers = dict(request.headers)

    # Validate webhook (handles challenge/echostr for setup)
    validation = await adapter.validate_webhook(body, headers)
    if validation is not None:
        # If it's a setup challenge, return it directly
        if "challenge" in validation or "echostr" in validation:
            return validation
        # Empty dict means validation passed, continue processing

    # Parse incoming message
    incoming = await adapter.parse_incoming(body, headers)
    if not incoming:
        return {"status": "ignored"}

    # Process with AI
    try:
        response_text = await _process_incoming_message(incoming)
    except Exception as e:
        logger.error(f"[Webhook] AI processing error: {e}")
        response_text = "抱歉，处理消息时出现错误。"

    # Send reply
    outgoing = OutgoingMessage(
        content=response_text,
        message_id=incoming.message_id,
        chat_id=incoming.chat_id,
        user_id=incoming.user_id,
    )

    success = await adapter.send_message(outgoing)

    return {"status": "ok" if success else "reply_failed"}
