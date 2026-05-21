"""Sub-Agent Executor - Sub-Agent 执行器

执行单个 Sub-Agent 的任务，支持上下文隔离和超时控制。
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.skills.loader import SkillLoader

from .sub_agent_models import (
    IsolatedContext,
    SubAgentConfig,
    SubAgentResult,
    SubAgentStatus,
)

logger = logging.getLogger(__name__)


class SubAgentExecutor:
    """Sub-Agent 执行器
    
    执行单个 Sub-Agent 的任务，支持：
    - 上下文隔离
    - 超时控制
    - 技能注入
    - 重试机制
    """
    
    def __init__(
        self,
        llm_handler: Optional[LLMBackend] = None,
        skill_loader: Optional[SkillLoader] = None,
    ):
        """初始化执行器
        
        Args:
            llm_handler: LLM 处理器
            skill_loader: 技能加载器
        """
        self.llm_handler = llm_handler
        self.skill_loader = skill_loader or SkillLoader()
        self._task_counter = 0
    
    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        self._task_counter += 1
        return f"subtask-{self._task_counter:06d}-{uuid.uuid4().hex[:8]}"
    
    def _create_isolated_context(
        self,
        agent_config: SubAgentConfig,
        parent_context: Optional[IsolatedContext] = None,
    ) -> IsolatedContext:
        """创建隔离上下文
        
        Args:
            agent_config: Sub-Agent 配置
            parent_context: 父上下文（用于继承共享数据）
        
        Returns:
            隔离上下文
        """
        task_id = self._generate_task_id()
        workspace = f"/tmp/workspace/{agent_config.agent_id}/{task_id}"
        uploads = f"{workspace}/uploads"
        outputs = f"{workspace}/outputs"
        
        # 创建目录
        for directory in [workspace, uploads, outputs]:
            os.makedirs(directory, exist_ok=True)
        
        shared_data = parent_context.shared_data if parent_context else {}
        
        context = IsolatedContext(
            agent_id=agent_config.agent_id,
            task_id=task_id,
            messages=[],
            workspace=workspace,
            uploads=uploads,
            outputs=outputs,
            shared_data=shared_data,
            parent_context=parent_context.task_id if parent_context else None,
        )
        
        logger.info(f"Created isolated context for {agent_config.agent_id}: {task_id}")
        return context
    
    def _build_system_prompt(
        self,
        agent_config: SubAgentConfig,
        skills: list[Any],
    ) -> str:
        """构建系统提示词
        
        Args:
            agent_config: Sub-Agent 配置
            skills: 加载的技能列表
        
        Returns:
            系统提示词
        """
        parts = []
        
        # Agent 自身的系统提示词
        if agent_config.system_prompt:
            parts.append(agent_config.system_prompt)
        
        # 技能提示词
        for skill in skills:
            if hasattr(skill, "system_prompt") and skill.system_prompt:
                parts.append(f"\n\n## Skill: {skill.name}\n{skill.system_prompt}")
        
        # 执行步骤
        steps_parts = []
        for skill in skills:
            if hasattr(skill, "steps") and skill.steps:
                steps_parts.extend(skill.steps)
        
        if steps_parts:
            parts.append("\n\n## Execution Steps\n")
            for i, step in enumerate(steps_parts, 1):
                parts.append(f"{i}. {step}")
        
        # 输出格式
        for skill in skills:
            if hasattr(skill, "output_format") and skill.output_format:
                parts.append(f"\n\n## Output Format\n{skill.output_format}")
        
        return "\n".join(parts)
    
    async def execute(
        self,
        agent_config: SubAgentConfig,
        task_params: dict,
        context: Optional[IsolatedContext] = None,
        llm_handler: Optional[LLMBackend] = None,
        parent_context: Optional[IsolatedContext] = None,
    ) -> SubAgentResult:
        """执行 Sub-Agent 任务
        
        Args:
            agent_config: Sub-Agent 配置
            task_params: 任务参数
            context: 预创建的上下文（可选）
            llm_handler: LLM 处理器（覆盖默认）
            parent_context: 父上下文（用于继承）
        
        Returns:
            执行结果
        """
        started_at = datetime.now()
        start_time = time.monotonic()
        
        # 使用传入的 llm_handler 或默认
        handler = llm_handler or self.llm_handler
        
        # 创建隔离上下文
        if not context:
            context = self._create_isolated_context(agent_config, parent_context)
        
        # 加载技能
        skills = []
        skill_names = task_params.get("skills", agent_config.default_skills)
        for skill_name in skill_names:
            skill = self.skill_loader.load_skill(skill_name)
            if skill:
                skills.append(skill)
        
        logger.info(
            f"Executing Sub-Agent {agent_config.agent_id} with {len(skills)} skills"
        )
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt(agent_config, skills)
        
        # 构建用户消息
        user_message = task_params.get("input", "")
        if isinstance(user_message, dict):
            user_message = "\n".join(f"{k}: {v}" for k, v in user_message.items())
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message),
        ]
        
        # 保存到上下文
        context.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        result = SubAgentResult(
            task_id=context.task_id,
            agent_id=agent_config.agent_id,
            agent_name=agent_config.name,
            status=SubAgentStatus.RUNNING,
            started_at=started_at,
        )
        
        try:
            if not handler:
                result.status = SubAgentStatus.FAILED
                result.error_message = "No LLM handler available"
                result.completed_at = datetime.now()
                result.duration_ms = int((time.monotonic() - start_time) * 1000)
                return result
            
            # 执行 LLM 调用
            timeout = task_params.get("timeout", agent_config.timeout)
            max_retries = agent_config.max_retries
            
            for retry in range(max_retries + 1):
                try:
                    output = await asyncio.wait_for(
                        handler.chat(messages),
                        timeout=timeout,
                    )
                    
                    result.status = SubAgentStatus.COMPLETED
                    result.output = output.content if hasattr(output, "content") else str(output)
                    result.retries = retry
                    
                    # Token 统计
                    if hasattr(output, "token_usage"):
                        result.token_usage = output.token_usage
                    
                    logger.info(
                        f"Sub-Agent {agent_config.agent_id} completed successfully "
                        f"(retry: {retry}, duration: {result.duration_ms}ms)"
                    )
                    break
                    
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Sub-Agent {agent_config.agent_id} timeout "
                        f"(retry: {retry}/{max_retries})"
                    )
                    if retry == max_retries:
                        result.status = SubAgentStatus.TIMEOUT
                        result.error_message = f"Timeout after {timeout}s"
                    
                except Exception as e:
                    logger.error(
                        f"Sub-Agent {agent_config.agent_id} error: {e} "
                        f"(retry: {retry}/{max_retries})"
                    )
                    if retry == max_retries:
                        result.status = SubAgentStatus.FAILED
                        result.error_message = str(e)
            
            result.completed_at = datetime.now()
            result.duration_ms = int((time.monotonic() - start_time) * 1000)
            
            return result
            
        except Exception as e:
            logger.error(f"Sub-Agent {agent_config.agent_id} unexpected error: {e}")
            result.status = SubAgentStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            result.duration_ms = int((time.monotonic() - start_time) * 1000)
            return result
    
    async def execute_streaming(
        self,
        agent_config: SubAgentConfig,
        task_params: dict,
        context: Optional[IsolatedContext] = None,
        llm_handler: Optional[LLMBackend] = None,
        parent_context: Optional[IsolatedContext] = None,
    ):
        """执行 Sub-Agent 任务（流式）
        
        Args:
            agent_config: Sub-Agent 配置
            task_params: 任务参数
            context: 预创建的上下文（可选）
            llm_handler: LLM 处理器（覆盖默认）
            parent_context: 父上下文（用于继承）
        
        Yields:
            流式输出事件
        """
        started_at = datetime.now()
        start_time = time.monotonic()
        
        handler = llm_handler or self.llm_handler
        
        if not context:
            context = self._create_isolated_context(agent_config, parent_context)
        
        # 发送开始事件
        yield {
            "event": "start",
            "data": {
                "task_id": context.task_id,
                "agent_id": agent_config.agent_id,
                "agent_name": agent_config.name,
                "skills": agent_config.default_skills,
            }
        }
        
        # 加载技能
        skills = []
        skill_names = task_params.get("skills", agent_config.default_skills)
        for skill_name in skill_names:
            skill = self.skill_loader.load_skill(skill_name)
            if skill:
                skills.append(skill)
                yield {
                    "event": "skill_loaded",
                    "data": {"skill": skill_name, "description": getattr(skill, "description", "")}
                }
        
        # 构建消息
        system_prompt = self._build_system_prompt(agent_config, skills)
        user_message = task_params.get("input", "")
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message),
        ]
        
        # 执行流式调用
        try:
            if handler and hasattr(handler, "stream_chat"):
                async for chunk in handler.stream_chat(messages):
                    yield {
                        "event": "chunk",
                        "data": {"content": chunk.content if hasattr(chunk, "content") else str(chunk)}
                    }
            elif handler:
                # 如果不支持流式，使用普通调用后发送完整内容
                output = await handler.chat(messages)
                yield {
                    "event": "chunk",
                    "data": {"content": output.content if hasattr(output, "content") else str(output)}
                }
            
            yield {
                "event": "done",
                "data": {
                    "task_id": context.task_id,
                    "duration_ms": int((time.monotonic() - start_time) * 1000),
                    "outputs_dir": context.outputs,
                }
            }
            
        except asyncio.TimeoutError:
            yield {
                "event": "error",
                "data": {"error": f"Timeout after {agent_config.timeout}s"}
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": {"error": str(e)}
            }
    
    def cleanup_context(self, context: IsolatedContext) -> None:
        """清理上下文
        
        Args:
            context: 要清理的上下文
        """
        import shutil
        
        if context.workspace and os.path.exists(context.workspace):
            try:
                shutil.rmtree(context.workspace)
                logger.info(f"Cleaned up workspace: {context.workspace}")
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace: {e}")