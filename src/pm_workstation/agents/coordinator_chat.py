"""Coordinator Chat Agent - 主会话 Agent

负责理解用户意图、任务规划和分发的核心 Agent。
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.chat.chat_models import (
    ChatMessage,
    CoordinatorResponse,
    IntentAnalysis,
    TaskMode,
    TaskPlan,
    TaskResult,
    TaskStatus,
)
from pm_workstation.chat.task_router import TaskRouter
from pm_workstation.memory.memory_retriever import MemoryRetriever
from pm_workstation.memory.soul_manager import SoulManager

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """你是一个专业的 AI 产品经理助手，负责帮助用户完成产品规划和管理工作。

你的能力包括：
1. **需求分析** - 帮助用户梳理和结构化产品需求
2. **原型设计** - 根据需求生成高保真原型
3. **文档撰写** - 生成专业的 PRD 产品需求文档
4. **市场调研** - 进行市场分析和竞品研究

当用户描述一个需求时，你应该：
1. 理解用户的意图和需求
2. 判断应该使用哪种任务模式
3. 如果需求不清晰，提出澄清问题
4. 执行任务并返回结果

请用友好、专业的语气回复用户，必要时使用 Markdown 格式化输出。
"""


class CoordinatorChatAgent:
    """主会话 Agent

    负责理解用户意图、任务规划和分发。
    """

    def __init__(
        self,
        llm_handler: Optional[LLMBackend] = None,
        task_router: Optional[TaskRouter] = None,
        memory_retriever: Optional[MemoryRetriever] = None,
        soul_manager: Optional[SoulManager] = None,
    ):
        """初始化主 Agent

        Args:
            llm_handler: LLM 处理器
            task_router: 任务路由器
            memory_retriever: 记忆检索器
            soul_manager: Soul 管理器
        """
        self.llm_handler = llm_handler
        self.task_router = task_router or TaskRouter(llm_handler)
        self.memory_retriever = memory_retriever
        self.soul_manager = soul_manager

    async def build_system_prompt(self, user_id: str, context_text: str = "") -> str:
        """构建包含 Soul 和记忆的增强系统提示词

        Args:
            user_id: 用户 ID
            context_text: 上下文文本，用于检索相关记忆

        Returns:
            增强的系统提示词
        """
        parts = []

        # 添加 Soul 提示词
        if self.soul_manager:
            soul = await self.soul_manager.get_active_soul(user_id)
            soul_prompt = self.soul_manager.build_soul_prompt(soul)
            parts.append(soul_prompt)
        else:
            parts.append(DEFAULT_SYSTEM_PROMPT)

        # 添加记忆提示词
        if self.memory_retriever and context_text:
            memory_prompt = await self.memory_retriever.build_memory_prompt(
                user_id=user_id,
                context=context_text,
            )
            if memory_prompt:
                parts.append(memory_prompt)

            # 添加用户偏好
            pref_prompt = await self.memory_retriever.get_user_preferences_prompt(user_id)
            if pref_prompt:
                parts.append(pref_prompt)

        return "\n\n".join(parts)

    async def process_message(
        self,
        message: str,
        context: list[ChatMessage],
        selected_skills: Optional[list[str]] = None,
        task_mode: Optional[TaskMode] = None,
        user_id: str = "default",
    ) -> CoordinatorResponse:
        """处理用户消息

        Args:
            message: 用户消息
            context: 上下文消息列表
            selected_skills: 选中的技能列表
            task_mode: 指定的任务模式（可选）
            user_id: 用户 ID，用于记忆检索

        Returns:
            主 Agent 响应
        """
        logger.info(f"Processing message: {message[:50]}...")

        # 如果没有 LLM 处理器，使用简单模式
        if not self.llm_handler:
            return await self._simple_process(message, selected_skills, task_mode)

        # 构建上下文文本
        context_text = message
        if context:
            recent_messages = context[-5:]
            context_text += "\n" + "\n".join(
                [f"{m.role}: {m.content[:100]}" for m in recent_messages]
            )

        # 构建增强系统提示词（包含 Soul 和记忆）
        system_prompt = await self.build_system_prompt(user_id, context_text)

        # 使用 LLM 分析意图
        intent = await self.analyze_intent(message, context, system_prompt=system_prompt)

        # 如果需要澄清
        if intent.requires_clarification:
            return CoordinatorResponse(
                message=self._format_clarification_message(intent),
                requires_user_input=True,
            )

        # 确定任务模式
        effective_mode = task_mode or intent.task_mode
        if not effective_mode:
            return CoordinatorResponse(
                message="我理解您的需求，但不确定应该执行哪种任务。请选择一个任务模式：\n\n"
                "1. **需求分析** - 梳理和结构化需求\n"
                "2. **原型设计** - 生成高保真原型\n"
                "3. **文档撰写** - 生成 PRD 文档\n"
                "4. **市场调研** - 进行市场分析\n\n"
                "请告诉我您需要哪种帮助，或者直接描述您的需求。",
                requires_user_input=True,
                suggested_actions=["需求分析", "原型设计", "文档撰写", "市场调研"],
            )

        # 创建任务计划
        task_plan = TaskPlan(
            task_id=f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_mode=effective_mode,
            description=f"执行 {effective_mode.value} 任务",
            params={"requirement_text": message},
        )

        # 执行任务
        result = await self.task_router.execute_task(
            mode=effective_mode,
            params={"requirement_text": message},
            selected_skills=selected_skills,
        )

        # 格式化响应
        response_message = await self._format_response(result, effective_mode)

        return CoordinatorResponse(
            message=response_message,
            task_plans=[task_plan],
            task_results=[result],
        )

    async def analyze_intent(
        self,
        message: str,
        context: list[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> IntentAnalysis:
        """分析用户意图

        Args:
            message: 用户消息
            context: 上下文消息列表
            system_prompt: 系统提示词（可选，包含 Soul 和记忆）

        Returns:
            意图分析结果
        """
        # 构建上下文
        context_text = ""
        if context:
            recent_messages = context[-5:]  # 最近 5 条消息
            context_text = "\n".join(
                [f"{m.role}: {m.content[:100]}" for m in recent_messages]
            )

        prompt = f"""请分析以下用户消息的意图，判断应该使用哪种任务模式。

上下文消息：
{context_text}

用户消息：{message}

可用的任务模式：
- requirement: 需求分析（用户想要梳理、结构化需求）
- prototype: 原型设计（用户想要生成界面原型）
- prd: 文档撰写（用户想要生成 PRD 文档）
- market_research: 市场调研（用户想要进行市场分析）

请返回 JSON 格式的结果：
{{
    "intent": "意图描述",
    "confidence": 0.95,
    "task_mode": "requirement/prototype/prd/market_research",
    "requires_clarification": false,
    "clarification_questions": []
}}

如果用户的需求不明确，设置 requires_clarification 为 true，并提供澄清问题。
"""

        try:
            response = await self.llm_handler.chat([
                LLMMessage(role="system", content=system_prompt or DEFAULT_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ])

            # 解析 JSON 响应
            result = json.loads(response.content)
            return IntentAnalysis(**result)

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            # 降级到简单匹配
            return self._simple_intent_analysis(message)

    def _simple_intent_analysis(self, message: str) -> IntentAnalysis:
        """简单的意图分析（无 LLM 时使用）

        Args:
            message: 用户消息

        Returns:
            意图分析结果
        """
        message_lower = message.lower()

        # 关键词匹配
        if any(kw in message_lower for kw in ["原型", "界面", "ui", "页面", "设计"]):
            return IntentAnalysis(
                intent="原型设计",
                confidence=0.8,
                task_mode=TaskMode.PROTOTYPE,
            )
        elif any(kw in message_lower for kw in ["prd", "文档", "需求文档", "撰写"]):
            return IntentAnalysis(
                intent="文档撰写",
                confidence=0.8,
                task_mode=TaskMode.PRD,
            )
        elif any(kw in message_lower for kw in ["市场", "调研", "竞品", "分析"]):
            return IntentAnalysis(
                intent="市场调研",
                confidence=0.8,
                task_mode=TaskMode.MARKET_RESEARCH,
            )
        elif any(kw in message_lower for kw in ["需求", "功能", "特性"]):
            return IntentAnalysis(
                intent="需求分析",
                confidence=0.8,
                task_mode=TaskMode.REQUIREMENT,
            )
        else:
            return IntentAnalysis(
                intent="未知",
                confidence=0.5,
                requires_clarification=True,
                clarification_questions=["请问您想要我帮您做什么？"],
            )

    async def _simple_process(
        self,
        message: str,
        selected_skills: Optional[list[str]] = None,
        task_mode: Optional[TaskMode] = None,
    ) -> CoordinatorResponse:
        """简单处理模式（无 LLM 时使用）

        Args:
            message: 用户消息
            selected_skills: 选中的技能列表
            task_mode: 指定的任务模式

        Returns:
            主 Agent 响应
        """
        # 使用简单意图分析
        intent = self._simple_intent_analysis(message)
        effective_mode = task_mode or intent.task_mode

        if not effective_mode:
            return CoordinatorResponse(
                message="请选择一个任务模式：\n\n"
                "1. **需求分析** - 梳理和结构化需求\n"
                "2. **原型设计** - 生成高保真原型\n"
                "3. **文档撰写** - 生成 PRD 文档\n"
                "4. **市场调研** - 进行市场分析",
                requires_user_input=True,
                suggested_actions=["需求分析", "原型设计", "文档撰写", "市场调研"],
            )

        # 执行任务
        result = await self.task_router.execute_task(
            mode=effective_mode,
            params={"requirement_text": message},
            selected_skills=selected_skills,
        )

        # 格式化响应
        response_message = await self._format_response(result, effective_mode)

        return CoordinatorResponse(
            message=response_message,
            task_results=[result],
        )

    def _format_clarification_message(self, intent: IntentAnalysis) -> str:
        """格式化澄清消息

        Args:
            intent: 意图分析结果

        Returns:
            格式化的消息
        """
        questions = "\n".join(
            [f"- {q}" for q in intent.clarification_questions]
        )
        return f"为了更好地帮助您，我需要了解更多信息：\n\n{questions}\n\n请提供更多细节，以便我为您执行正确的任务。"

    async def _format_response(
        self, result: TaskResult, mode: TaskMode
    ) -> str:
        """格式化任务结果响应

        Args:
            result: 任务结果
            mode: 任务模式

        Returns:
            格式化的响应消息
        """
        mode_labels = {
            TaskMode.REQUIREMENT: "需求分析",
            TaskMode.PROTOTYPE: "原型设计",
            TaskMode.PRD: "文档撰写",
            TaskMode.MARKET_RESEARCH: "市场调研",
        }

        mode_label = mode_labels.get(mode, "任务")

        if result.status == TaskStatus.FAILED:
            # 检查是否是 LLM 相关错误
            error_msg = result.error_message or ""
            if "LLM" in error_msg or "Forbidden" in error_msg or "handler" in error_msg.lower():
                return (
                    f"**{mode_label}** 功能暂时不可用\n\n"
                    f"当前 LLM 服务未正确配置，无法执行{mode_label}任务。\n\n"
                    f"请在 **设置 > LLM 配置** 中配置有效的 LLM API Key 后重试。\n\n"
                    f"如果您只是想了解系统功能，可以尝试：\n"
                    f"- 查看 **PM Skills** 了解可用的技能\n"
                    f"- 查看 **原型预览** 查看已生成的原型\n"
                    f"- 查看 **文档查看** 查看已生成的文档"
                )
            return f"任务执行失败：{error_msg}\n\n请稍后重试，或尝试简化您的需求。"

        response = f"**{mode_label}** 任务已完成！\n\n"

        if result.output:
            response += result.output + "\n\n"

        if result.artifacts:
            response += "### 产出物\n\n"
            for artifact in result.artifacts:
                response += f"- [{artifact.name}]({artifact.url})\n"

        return response
