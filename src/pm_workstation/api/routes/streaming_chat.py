"""Streaming Chat API - 流式会话 API

使用 Server-Sent Events (SSE) 实现流式响应，实时展示 AI 思考过程。
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from pm_workstation.agents.coordinator_chat import CoordinatorChatAgent
from pm_workstation.agents.pm_sub_agents import register_pm_sub_agents
from pm_workstation.agents.sub_agent_executor import SubAgentExecutor
from pm_workstation.agents.sub_agent_models import SubAgentConfig
from pm_workstation.agents.sub_agent_registry import get_sub_agent_registry
from pm_workstation.api.routes.chat import (
    _get_chat_manager,
    _memory_retriever,
    _soul_manager,
    _token_usage_store,
)
from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.chat.chat_models import (
    ChatMessage,
    TaskMode,
    TaskStatus,
)
from pm_workstation.component_library.store import ComponentTemplateStore
from pm_workstation.knowledge_base.store import TemplateStore
from pm_workstation.model_router.base import LLMMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["会话交互-流式"])


async def _build_llm_handler_for_streaming(request: Request, provider_id: str | None = None, model_name: str | None = None):
    """构建 LLM Handler 用于流式响应"""
    from pm_workstation.api.app import _build_llm_handler

    provider_store = request.app.state.provider_store

    if provider_id:
        config = await provider_store.get_config(provider_id)
    else:
        config = await provider_store.get_default_config()

    if config:
        return _build_llm_handler(config, model_override=model_name)
    return None


async def _get_sub_agent_for_task(task_mode: TaskMode) -> SubAgentConfig | None:
    """根据任务模式获取合适的 Sub-Agent"""
    registry = get_sub_agent_registry()

    capability_map = {
        TaskMode.REQUIREMENT: "requirement",
        TaskMode.PROTOTYPE: "prototype",
        TaskMode.PRD: "prd",
        TaskMode.MARKET_RESEARCH: "market-research",
    }

    capability = capability_map.get(task_mode)
    if capability:
        agents = registry.match_by_capability(capability)
        if agents:
            return agents[0]

    return None


@router.post("/sessions/{session_id}/stream", summary="流式发送消息")
async def stream_message(
    session_id: str,
    body: dict,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """流式发送消息并实时展示 AI 思考过程

    SSE Event Types:
    - intent_analysis: 意图分析完成
    - task_routing: 任务路由完成
    - skill_loading: 技能加载
    - sub_agent_selected: Sub-Agent 选择
    - chunk: 内容片段
    - thinking: 思考步骤
    - artifact: 产物生成
    - done: 完成
    - error: 错误
    """
    session = await _get_chat_manager().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    task_mode_str = body.get("task_mode")
    selected_skills = body.get("selected_skills", [])
    provider_id = body.get("provider_id")
    model_name = body.get("model_name")
    template_id = body.get("template_id")

    async def event_generator():
        start_time = time.monotonic()
        accumulated_content = ""

        try:
            # Event 1: Intent Analysis
            yield f"event: intent_analysis_start\ndata: {json.dumps({'status': 'analyzing'})}\n\n"
            await asyncio.sleep(0.1)

            # 构建 LLM Handler
            llm_handler = await _build_llm_handler_for_streaming(request, provider_id, model_name)

            # 意图分析
            intent_result = {
                "intent": "chat",
                "confidence": 0.8,
                "task_mode": task_mode_str or None,
                "suggested_skills": selected_skills,
            }

            if llm_handler:
                try:
                    coordinator = CoordinatorChatAgent(
                        llm_handler=llm_handler,
                        memory_retriever=_memory_retriever,
                        soul_manager=_soul_manager,
                    )

                    analysis = await asyncio.wait_for(
                        coordinator.analyze_intent(content, user_id),
                        timeout=10.0
                    )
                    if analysis:
                        intent_result = {
                            "intent": analysis.intent,
                            "confidence": analysis.confidence or 0.8,
                            "task_mode": analysis.task_mode.value if analysis.task_mode else None,
                            "suggested_skills": selected_skills or [],
                            "clarification_needed": analysis.clarification_questions if analysis.clarification_questions else [],
                        }
                except TimeoutError:
                    logger.warning("Intent analysis timeout, using default")
                except Exception as e:
                    logger.error(f"Intent analysis error: {e}")

            yield f"event: intent_analysis\ndata: {json.dumps(intent_result)}\n\n"

            # Event 2: Task Routing
            task_mode = TaskMode(task_mode_str) if task_mode_str else None
            if not task_mode and intent_result.get("task_mode"):
                try:
                    task_mode = TaskMode(intent_result["task_mode"])
                except ValueError:
                    pass

            routing_result = {
                "mode": task_mode.value if task_mode else "chat",
                "skills": selected_skills,
                "use_sub_agent": task_mode is not None,
            }

            yield f"event: task_routing\ndata: {json.dumps(routing_result)}\n\n"

            # Event 3: Skill Loading
            if selected_skills:
                for skill_name in selected_skills:
                    yield f"event: skill_loading\ndata: {json.dumps({'skill': skill_name, 'status': 'loaded'})}\n\n"
                    await asyncio.sleep(0.05)

            # Event 4: Sub-Agent Selection
            sub_agent_config = None
            if task_mode:
                sub_agent_config = await _get_sub_agent_for_task(task_mode)
                if sub_agent_config:
                    yield f"event: sub_agent_selected\ndata: {json.dumps({'agent_id': sub_agent_config.agent_id, 'name': sub_agent_config.name})}\n\n"
                else:
                    yield f"event: sub_agent_selected\ndata: {json.dumps({'agent_id': None, 'name': None, 'fallback': True})}\n\n"

            # Event 5: Content Generation
            yield f"event: generation_start\ndata: {json.dumps({'status': 'generating'})}\n\n"

            # 添加用户消息
            user_message = ChatMessage(
                id=uuid.uuid4().hex,
                session_id=session_id,
                role="user",
                content=content,
                task_mode=task_mode,
            )
            await _get_chat_manager().add_message(session_id, user_message)

            # 获取上下文
            context_messages = await _get_chat_manager().get_context_messages(session_id, limit=10)

            # 如果有模板，注入模板内容
            if template_id:
                try:
                    ts = TemplateStore()
                    tmpl = await ts.get(template_id)
                    if tmpl:
                        template_context = ChatMessage(
                            id="template_ctx",
                            session_id=session_id,
                            role="system",
                            content=f"[模板: {tmpl.name}]\n{tmpl.content}",
                        )
                        context_messages = [*context_messages, template_context]
                        yield f"event: template_loaded\ndata: {json.dumps({'template': tmpl.name, 'type': tmpl.type.value})}\n\n"
                    else:
                        cs = ComponentTemplateStore()
                        comp = await cs.get(template_id)
                        if comp:
                            template_context = ChatMessage(
                                id="template_ctx",
                                session_id=session_id,
                                role="system",
                                content=f"[组件模板: {comp.name}]\n{comp.content}",
                            )
                            context_messages = [*context_messages, template_context]
                            yield f"event: template_loaded\ndata: {json.dumps({'template': comp.name, 'type': 'prototype'})}\n\n"
                except Exception as e:
                    logger.warning(f"Template loading error: {e}")

            # 执行生成
            if sub_agent_config and llm_handler:
                # 使用 Sub-Agent 执行
                executor = SubAgentExecutor(llm_handler=llm_handler)

                thinking_step_id = 0
                for event in await executor.execute(
                    agent_config=sub_agent_config,
                    task_params={
                        "input": content,
                        "skills": selected_skills or sub_agent_config.default_skills,
                    },
                    llm_handler=llm_handler,
                ):
                    if event.get("event") == "chunk":
                        chunk_content = event["data"].get("content", "")
                        accumulated_content += chunk_content

                        yield f"event: chunk\ndata: {json.dumps({'content': chunk_content, 'accumulated': accumulated_content})}\n\n"

                    elif event.get("event") == "skill_loaded":
                        skill_name = event["data"].get("skill", "")
                        yield f"event: thinking\ndata: {json.dumps({'step': f'skill_{thinking_step_id}', 'description': f'加载技能: {skill_name}', 'status': 'completed'})}\n\n"
                        thinking_step_id += 1

                    elif event.get("event") == "error":
                        yield f"event: error\ndata: {json.dumps({'error': event['data'].get('error')})}\n\n"

                    elif event.get("event") == "done":
                        break

            elif llm_handler:
                coordinator = CoordinatorChatAgent(
                    llm_handler=llm_handler,
                    memory_retriever=_memory_retriever,
                    soul_manager=_soul_manager,
                )

                # 构建系统提示词
                system_prompt = await coordinator.build_system_prompt(user_id, content)

                messages = [
                    LLMMessage(role="system", content=system_prompt),
                ]

                # 添加上下文
                for msg in context_messages:
                    if msg.role == "user":
                        messages.append(LLMMessage(role="user", content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(LLMMessage(role="assistant", content=msg.content))
                    elif msg.role == "system" and msg.id == "template_ctx":
                        messages.append(LLMMessage(role="system", content=msg.content))

                messages.append(LLMMessage(role="user", content=content))

                # 流式生成
                if hasattr(llm_handler, "stream_chat"):
                    thinking_step_id = 0
                    yield f"event: thinking\ndata: {json.dumps({'step': 'llm_call', 'description': '开始调用 LLM', 'status': 'running'})}\n\n"

                    async for chunk in llm_handler.stream_chat(messages):
                        chunk_content = chunk.content if hasattr(chunk, "content") else str(chunk)
                        accumulated_content += chunk_content

                        yield f"event: chunk\ndata: {json.dumps({'content': chunk_content, 'accumulated': accumulated_content})}\n\n"

                        # 每 10 个 chunk 发送一个 thinking step
                        thinking_step_id += 1
                        if thinking_step_id % 10 == 0:
                            yield f"event: thinking\ndata: {json.dumps({'step': f'chunk_{thinking_step_id}', 'description': '生成内容...', 'status': 'running'})}\n\n"

                    yield f"event: thinking\ndata: {json.dumps({'step': 'llm_call', 'description': 'LLM 调用完成', 'status': 'completed'})}\n\n"
                else:
                    # 非流式，整体返回
                    response = await llm_handler.chat(messages)
                    accumulated_content = response.content if hasattr(response, "content") else str(response)

                    yield f"event: chunk\ndata: {json.dumps({'content': accumulated_content, 'accumulated': accumulated_content})}\n\n"

            else:
                # 无 LLM Handler
                accumulated_content = f"抱歉，当前没有可用的 LLM 服务。\n\n您发送的内容: {content}\n\n请先在「供应商配置」中配置 LLM 服务后再使用。"
                yield f"event: chunk\ndata: {json.dumps({'content': accumulated_content, 'accumulated': accumulated_content})}\n\n"

            # Event 6: Token Usage
            duration_ms = int((time.monotonic() - start_time) * 1000)
            prompt_tokens = max(1, len(content) // 4)
            completion_tokens = max(1, len(accumulated_content) // 4)
            total_tokens = prompt_tokens + completion_tokens

            yield f"event: token_usage\ndata: {json.dumps({'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'total_tokens': total_tokens, 'duration_ms': duration_ms})}\n\n"

            # 添加 AI 响应消息
            assistant_message = ChatMessage(
                id=uuid.uuid4().hex,
                session_id=session_id,
                role="assistant",
                content=accumulated_content,
                task_mode=task_mode,
                task_status=TaskStatus.COMPLETED if task_mode else None,
                thinking_time_ms=duration_ms,
                model_id=model_name or "default",
                token_usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
            )
            await _get_chat_manager().add_message(session_id, assistant_message)

            # Record token usage
            _token_usage_store.record(
                model_id=model_name or "default",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                source="chat_stream",
            )

            # Event 7: Done
            yield f"event: done\ndata: {json.dumps({'message_id': assistant_message.id, 'duration_ms': duration_ms, 'total_tokens': total_tokens})}\n\n"

        except TimeoutError:
            yield f"event: error\ndata: {json.dumps({'error': '处理超时，请简化需求后重试'})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/sub-agents", summary="获取 Sub-Agent 列表")
async def list_sub_agents():
    """获取所有已注册的 Sub-Agent"""
    registry = get_sub_agent_registry()

    # 确保 PM Sub-Agents 已注册
    if len(registry.list_all()) == 0:
        register_pm_sub_agents()

    stats = registry.get_stats()

    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "default_skills": a.default_skills,
                "timeout": a.timeout,
                "priority": a.priority,
                "enabled": a.enabled,
            }
            for a in registry.list_all()
        ],
        "stats": stats.model_dump(),
    }


@router.post("/sub-agents/match", summary="能力匹配")
async def match_sub_agents(body: dict):
    """根据能力匹配 Sub-Agent"""
    registry = get_sub_agent_registry()

    # 确保 PM Sub-Agents 已注册
    if len(registry.list_all()) == 0:
        register_pm_sub_agents()

    capabilities = body.get("capabilities", [])
    if not capabilities:
        capabilities = [body.get("capability")]

    matches = registry.match_by_capabilities(capabilities)

    return {
        "matches": [m.model_dump() for m in matches],
        "total": len(matches),
    }
