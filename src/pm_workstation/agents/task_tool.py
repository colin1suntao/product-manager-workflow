"""任务委派工具和子 Agent 执行器

实现 Coordinator 到 Sub-agent 的任务委派机制，支持并发执行。
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pm_workstation.agents.registry import SubAgentConfig
from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.skills.loader import SkillLoader


class IsolatedContext(BaseModel):
    """隔离的上下文模型"""

    agent_id: str
    task_id: str
    messages: list[dict[str, str]] = Field(default_factory=list)
    workspace: str = ""  # 工作空间目录
    uploads: str = ""  # 上传文件目录
    outputs: str = ""  # 输出文件目录
    shared_data: dict[str, Any] = Field(default_factory=dict)


class SubTask(BaseModel):
    """子任务模型"""

    id: str
    agent_id: str  # 目标 Agent ID
    description: str  # 任务描述
    input_data: dict[str, Any] = Field(default_factory=dict)  # 输入数据
    expected_output: str = ""  # 期望输出描述
    timeout: int = 300  # 超时时间 (秒)
    can_run_parallel: bool = True  # 是否可并行
    retry_count: int = 0  # 当前重试次数


class TaskRequest(BaseModel):
    """任务委派请求"""

    agent_id: str
    task_description: str
    context: dict[str, Any] = Field(default_factory=dict)
    timeout: int | None = None


class TaskResult(BaseModel):
    """任务执行结果"""

    task_id: str
    agent_id: str
    status: str  # success, failed, timeout
    output: str | None = None  # 输出结果
    error: str | None = None  # 错误信息
    duration: float = 0.0  # 执行时长 (秒)
    token_usage: dict[str, int] = Field(default_factory=dict)  # Token 使用量


class TaskDecomposition(BaseModel):
    """任务拆解结果"""

    plan: str  # 执行计划描述
    subtasks: list[SubTask]
    execution_order: list[str]  # 子任务 ID 列表


class ContextManager:
    """上下文管理器

    为子 Agent 创建独立的上下文空间，隔离主 Agent 和其他子 Agent 的对话历史。
    """

    def __init__(self, workspace_dir: str | None = None):
        self.workspace_dir = workspace_dir or os.path.join(
            os.path.expanduser("~"),
            ".pm_workstation",
            "contexts",
        )
        self._contexts: dict[str, IsolatedContext] = {}

    def create_isolated_context(
        self,
        agent_id: str,
        task_id: str,
        shared_data: dict[str, Any],
    ) -> IsolatedContext:
        """创建隔离的上下文

        Args:
            agent_id: Agent ID
            task_id: 任务 ID
            shared_data: 共享数据（输入）

        Returns:
            隔离的上下文对象
        """
        # 创建工作空间目录
        task_workspace = os.path.join(self.workspace_dir, agent_id, task_id)
        uploads_dir = os.path.join(task_workspace, "uploads")
        outputs_dir = os.path.join(task_workspace, "outputs")

        # 确保目录存在
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(outputs_dir, exist_ok=True)

        context = IsolatedContext(
            agent_id=agent_id,
            task_id=task_id,
            workspace=task_workspace,
            uploads=uploads_dir,
            outputs=outputs_dir,
            shared_data=shared_data,
        )

        context_key = f"{agent_id}:{task_id}"
        self._contexts[context_key] = context
        return context

    def get_context(self, agent_id: str, task_id: str) -> IsolatedContext | None:
        """获取上下文

        Args:
            agent_id: Agent ID
            task_id: 任务 ID

        Returns:
            隔离的上下文对象，如果不存在返回 None
        """
        context_key = f"{agent_id}:{task_id}"
        return self._contexts.get(context_key)

    def merge_results(
        self,
        main_context: dict[str, Any],
        sub_results: dict[str, Any],
    ) -> dict[str, Any]:
        """合并子任务结果到主上下文

        Args:
            main_context: 主上下文
            sub_results: 子任务结果映射 {task_id: result}

        Returns:
            更新后的主上下文
        """
        main_context["subtask_results"] = sub_results
        return main_context

    def clear_context(self, agent_id: str, task_id: str) -> None:
        """清理上下文

        Args:
            agent_id: Agent ID
            task_id: 任务 ID
        """
        context_key = f"{agent_id}:{task_id}"
        context = self._contexts.pop(context_key, None)

        # 可选：清理工作空间目录
        # 注意：如果输出需要保留，不要删除 outputs 目录
        if context and context.workspace:
            uploads_path = Path(context.uploads)
            if uploads_path.exists():
                # 只清理上传目录，保留输出目录
                for item in uploads_path.iterdir():
                    if item.is_file():
                        item.unlink()

    def list_active_contexts(self) -> list[IsolatedContext]:
        """列出所有活跃的上下文

        Returns:
            活跃上下文列表
        """
        return list(self._contexts.values())


class SubAgentExecutor:
    """子 Agent 执行器

    执行子 Agent 任务，使用 LLM 调用并处理超时和错误。
    """

    def __init__(
        self,
        llm_factory: Any,  # LLMFactory
        context_manager: ContextManager | None = None,
        skill_loader: SkillLoader | None = None,
    ):
        self.llm_factory = llm_factory
        self.context_manager = context_manager or ContextManager()
        self.skill_loader = skill_loader or SkillLoader()

    async def execute(
        self,
        config: SubAgentConfig,
        task: str,
        context: IsolatedContext | dict[str, Any],
        timeout: int | None = None,
    ) -> str:
        """执行子 Agent 任务

        Args:
            config: Sub-agent 配置
            task: 任务描述
            context: 上下文数据
            timeout: 超时时间（秒），如果为 None 则使用配置的超时

        Returns:
            执行结果字符串

        Raises:
            TimeoutError: 如果任务超时
            Exception: 如果执行失败
        """
        effective_timeout = timeout or config.timeout_seconds

        # 构建消息
        messages = self._build_messages(config, task, context)

        # 获取 LLM 处理器
        llm_handler = self._get_llm_handler(config)

        # 执行 LLM 调用
        try:
            response = await asyncio.wait_for(
                llm_handler.chat(messages),
                timeout=effective_timeout,
            )
            return response.content
        except TimeoutError:
            raise TimeoutError(
                f"Sub-agent '{config.id}' timed out after {effective_timeout}s"
            )

    def _build_messages(
        self,
        config: SubAgentConfig,
        task: str,
        context: IsolatedContext | dict[str, Any],
    ) -> list[LLMMessage]:
        """构建 LLM 消息

        Args:
            config: Sub-agent 配置
            task: 任务描述
            context: 上下文数据（IsolatedContext 或字典）

        Returns:
            消息列表
        """
        system_prompt = config.system_prompt

        # 如果有技能，注入技能系统提示
        skills_info = self._get_skills_info(config.skills)
        if skills_info:
            system_prompt += "\n\n## 可用技能\n" + skills_info

        user_message = task

        # 提取 shared_data
        if isinstance(context, IsolatedContext):
            shared_data = context.shared_data
        else:
            shared_data = context.get("shared_data", {})

        if shared_data:
            user_message += "\n\n## 上下文数据\n" + str(shared_data)

        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message),
        ]

    def _get_llm_handler(self, config: SubAgentConfig) -> LLMBackend:
        """获取 LLM 处理器

        Args:
            config: Sub-agent 配置

        Returns:
            LLM 处理器
        """
        # 根据配置获取对应的 LLM 处理器
        if config.model == "inherit" or config.model == "use_default":
            return self.llm_factory.get_default()
        else:
            return self.llm_factory.get_by_model(config.model)

    def _get_skills_info(self, skills: list[str]) -> str:
        """获取技能信息

        Args:
            skills: 技能列表

        Returns:
            技能信息字符串
        """
        if not skills:
            return ""

        skill_parts = []
        for skill_name in skills:
            skill = self.skill_loader.load(skill_name)
            if skill:
                skill_parts.append(skill.get_full_prompt())
            else:
                skill_parts.append(f"- {skill_name}")

        return "\n\n".join(skill_parts)


class TaskDelegationTool:
    """任务委派工具

    Coordinator 通过此工具向 Sub-agent 委派任务，支持批量并发执行（最多 3 个）。
    """

    def __init__(
        self,
        registry: Any,  # SubAgentRegistry
        executor: SubAgentExecutor,
        max_concurrent: int = 3,
    ):
        self.registry = registry
        self.executor = executor
        self.max_concurrent = max_concurrent

    async def invoke(
        self,
        agent_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> TaskResult:
        """委派任务到指定 Sub-agent

        Args:
            agent_id: 目标 Agent ID
            task_description: 任务描述
            context: 上下文数据
            timeout: 超时时间（秒）

        Returns:
            任务执行结果

        Raises:
            KeyError: 如果 Agent 不存在
        """
        config = self.registry.get(agent_id)
        if config is None:
            raise KeyError(f"Sub-agent '{agent_id}' not found")

        task_id = f"task-{agent_id}-{int(time.time())}"
        ctx = context or {}

        # 创建隔离上下文
        isolated_ctx = self.executor.context_manager.create_isolated_context(
            agent_id, task_id, ctx
        )

        start_time = time.monotonic()
        try:
            output = await self.executor.execute(
                config=config,
                task=task_description,
                context=isolated_ctx,
                timeout=timeout,
            )
            duration = time.monotonic() - start_time

            return TaskResult(
                task_id=task_id,
                agent_id=agent_id,
                status="success",
                output=output,
                duration=duration,
            )
        except TimeoutError as e:
            duration = time.monotonic() - start_time
            return TaskResult(
                task_id=task_id,
                agent_id=agent_id,
                status="timeout",
                error=str(e),
                duration=duration,
            )
        except Exception as e:
            duration = time.monotonic() - start_time
            return TaskResult(
                task_id=task_id,
                agent_id=agent_id,
                status="failed",
                error=str(e),
                duration=duration,
            )
        finally:
            # 清理上下文
            self.executor.context_manager.clear_context(agent_id, task_id)

    async def invoke_batch(
        self,
        tasks: list[TaskRequest],
    ) -> list[TaskResult]:
        """批量委派任务（支持并发）

        Args:
            tasks: 任务请求列表

        Returns:
            任务结果列表
        """
        if not tasks:
            return []

        # 限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_invoke(task: TaskRequest) -> TaskResult:
            async with semaphore:
                return await self.invoke(
                    agent_id=task.agent_id,
                    task_description=task.task_description,
                    context=task.context,
                    timeout=task.timeout,
                )

        results = await asyncio.gather(
            *[limited_invoke(task) for task in tasks],
            return_exceptions=False,
        )
        return list(results)
