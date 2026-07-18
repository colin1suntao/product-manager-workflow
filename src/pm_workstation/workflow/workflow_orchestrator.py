"""Workflow Orchestrator - 工作流编排器

执行复杂的多步骤工作流，支持：
- 依赖管理
- 并行执行
- 超时控制
- 重试机制
- 进度追踪
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from pm_workstation.agents.sub_agent_executor import SubAgentExecutor
from pm_workstation.agents.sub_agent_models import SubAgentStatus
from pm_workstation.agents.sub_agent_registry import get_sub_agent_registry
from pm_workstation.chat.task_router import TaskRouter
from pm_workstation.model_router.base import LLMBackend

from .workflow_models import (
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowProgress,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """工作流编排器
    
    执行预定义的多步骤工作流，支持：
    - 步骤依赖管理（等待前置步骤完成）
    - 并行执行（同时运行多个步骤）
    - 超时控制（每个步骤独立超时）
    - 重试机制（失败后自动重试）
    - 进度追踪（实时报告进度）
    """

    def __init__(
        self,
        llm_handler: LLMBackend | None = None,
        task_router: TaskRouter | None = None,
    ):
        """初始化编排器
        
        Args:
            llm_handler: LLM 处理器
            task_router: 任务路由器
        """
        self.llm_handler = llm_handler
        self.task_router = task_router or TaskRouter(llm_handler)
        self.registry = get_sub_agent_registry()
        self.executor = SubAgentExecutor(llm_handler)
        self._execution_counter = 0
        self._active_executions: dict[str, WorkflowExecution] = {}

    def _generate_execution_id(self) -> str:
        """生成执行 ID"""
        self._execution_counter += 1
        return f"wf-exec-{self._execution_counter:06d}-{uuid.uuid4().hex[:8]}"

    def _analyze_dependencies(self, workflow: WorkflowDefinition) -> dict[str, list[str]]:
        """分析步骤依赖关系
        
        Args:
            workflow: 工作流定义
        
        Returns:
            步骤 ID 到其依赖步骤 ID 列表的映射
        """
        dependencies: dict[str, list[str]] = {}

        for step in workflow.steps:
            deps = []
            if step.depends_on:
                deps.append(step.depends_on)
            dependencies[step.id] = deps

        return dependencies

    def _analyze_parallel_groups(self, workflow: WorkflowDefinition) -> list[list[str]]:
        """分析并行组（O(n α(n)) Union-Find）

        找出可以并行执行的步骤组

        Args:
            workflow: 工作流定义

        Returns:
            并行组列表（每个组是一组可并行执行的步骤 ID）
        """
        if not workflow.steps:
            return []

        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for step in workflow.steps:
            parent[step.id] = step.id

        for step in workflow.steps:
            if step.parallel_with:
                union(step.id, step.parallel_with)

        groups: dict[str, list[str]] = {}
        for step in workflow.steps:
            root = find(step.id)
            if root not in groups:
                groups[root] = []
            groups[root].append(step.id)

        return [g for g in groups.values() if len(g) > 1]

    def _get_ready_steps(
        self,
        workflow: WorkflowDefinition,
        completed_steps: set[str],
        running_steps: set[str],
        failed_steps: set[str],
    ) -> list[str]:
        """获取就绪的步骤（依赖已满足）
        
        Args:
            workflow: 工作流定义
            completed_steps: 已完成的步骤 ID
            running_steps: 正在运行的步骤 ID
            failed_steps: 已失败的步骤 ID
        
        Returns:
            就绪的步骤 ID 列表
        """
        ready = []

        for step in workflow.steps:
            # 已处理过的跳过
            if step.id in completed_steps or step.id in running_steps or step.id in failed_steps:
                continue

            # 检查依赖
            if step.depends_on:
                # 依赖未完成
                if step.depends_on not in completed_steps:
                    continue

                # 依赖失败且当前步骤非可选
                if step.depends_on in failed_steps and not step.optional:
                    continue

            # 如果有并行关系，检查并行步骤状态
            if step.parallel_with:
                # 并行步骤正在运行，可以一起运行
                if step.parallel_with in running_steps:
                    ready.append(step.id)
                # 并行步骤已完成，继续执行当前步骤
                elif step.parallel_with in completed_steps:
                    ready.append(step.id)
                # 并行步骤等待中，也加入就绪
                elif step.parallel_with not in running_steps:
                    ready.append(step.id)
            else:
                ready.append(step.id)

        return ready

    def _build_step_input(
        self,
        step: Any,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> dict:
        """构建步骤输入参数
        
        Args:
            step: 当前步骤
            workflow: 工作流定义
            execution: 执行记录
        
        Returns:
            输入参数字典
        """
        input_params = dict(step.input)

        # 从依赖步骤获取输入
        if step.depends_on and step.input_from_dependency:
            for result in execution.steps_results:
                if result.step_id == step.depends_on:
                    if result.output:
                        input_params[step.input_from_dependency] = result.output
                    if result.artifacts:
                        input_params["artifacts"] = result.artifacts
                    break

        return input_params

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        user_id: str,
        session_id: str | None = None,
        initial_input: dict | None = None,
        llm_handler: LLMBackend | None = None,
    ) -> WorkflowExecution:
        """执行工作流
        
        Args:
            workflow: 工作流定义
            user_id: 用户 ID
            session_id: 会话 ID（可选）
            initial_input: 初始输入参数
            llm_handler: LLM 处理器（覆盖默认）
        
        Returns:
            工作流执行记录
        """
        execution_id = self._generate_execution_id()
        handler = llm_handler or self.llm_handler

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            user_id=user_id,
            session_id=session_id,
            status=WorkflowStatus.RUNNING,
            total_steps=len(workflow.steps),
            started_at=datetime.now(),
        )

        # 保存初始输入到第一个步骤（深拷贝避免副作用）
        if initial_input and workflow.steps:
            workflow.steps[0].input = {**workflow.steps[0].input, **initial_input}

        self._active_executions[execution_id] = execution

        logger.info(f"Starting workflow execution: {execution_id} ({workflow.name})")

        completed_steps: set[str] = set()
        running_steps: set[str] = set()
        failed_steps: set[str] = set()
        skipped_steps: set[str] = set()

        step_map = {s.id: s for s in workflow.steps}

        start_time = time.monotonic()

        try:
            while len(completed_steps) + len(failed_steps) + len(skipped_steps) < len(workflow.steps):
                # 获取就绪步骤
                ready_step_ids = self._get_ready_steps(
                    workflow, completed_steps, running_steps, failed_steps
                )

                if not ready_step_ids:
                    # 检查是否所有步骤都已完成或失败
                    if not running_steps:
                        break

                    # 等待正在运行的步骤完成
                    await asyncio.sleep(0.5)
                    continue

                # 执行就绪的步骤（支持并行）
                step_tasks = []
                for step_id in ready_step_ids:
                    step = step_map[step_id]
                    running_steps.add(step_id)
                    execution.current_step_index = workflow.steps.index(step)

                    step_tasks.append(
                        self._execute_step(
                            step=step,
                            workflow=workflow,
                            execution=execution,
                            handler=handler,
                        )
                    )

                # 并行执行
                if len(step_tasks) > 1:
                    logger.info(f"Executing {len(step_tasks)} steps in parallel")
                    results = await asyncio.gather(*step_tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        step_id = ready_step_ids[i]
                        if isinstance(result, Exception):
                            logger.error(f"Step {step_id} failed with exception: {result}")
                            step = step_map[step_id]
                            step_result = StepResult(
                                step_id=step_id,
                                step_name=step.name,
                                status=StepStatus.FAILED,
                                error_message=str(result),
                            )
                            execution.steps_results.append(step_result)
                            failed_steps.add(step_id)
                            running_steps.discard(step_id)
                        else:
                            execution.steps_results.append(result)
                            running_steps.discard(step_id)
                            if result.status == StepStatus.COMPLETED:
                                completed_steps.add(step_id)
                            elif result.status == StepStatus.FAILED:
                                failed_steps.add(step_id)
                            elif result.status == StepStatus.SKIPPED:
                                skipped_steps.add(step_id)
                else:
                    # 单个步骤执行
                    result = await step_tasks[0]
                    execution.steps_results.append(result)
                    running_steps.discard(ready_step_ids[0])
                    if result.status == StepStatus.COMPLETED:
                        completed_steps.add(ready_step_ids[0])
                    elif result.status == StepStatus.FAILED:
                        failed_steps.add(ready_step_ids[0])
                    elif result.status == StepStatus.SKIPPED:
                        skipped_steps.add(ready_step_ids[0])

                # 更新统计
                execution.completed_steps = len(completed_steps)
                execution.failed_steps = len(failed_steps)

            # 汇总结果
            execution.completed_at = datetime.now()
            execution.total_duration_ms = int((time.monotonic() - start_time) * 1000)

            # 收集所有产物
            for result in execution.steps_results:
                if result.artifacts:
                    execution.final_artifacts.extend(result.artifacts)
                if result.token_usage:
                    for key, value in result.token_usage.items():
                        execution.total_token_usage[key] = (
                            execution.total_token_usage.get(key, 0) + value
                        )

            # 确定最终状态
            failed_mandatory = [
                s for s in workflow.steps
                if s.id in failed_steps and not s.optional
            ]

            if failed_mandatory:
                execution.status = WorkflowStatus.FAILED
                execution.error_message = f"关键步骤失败: {', '.join(s.name for s in failed_mandatory)}"
            elif failed_steps:
                execution.status = WorkflowStatus.COMPLETED  # 有失败但都是可选步骤
                execution.error_message = f"可选步骤失败: {', '.join(s.name for s in workflow.steps if s.id in failed_steps)}"
            else:
                execution.status = WorkflowStatus.COMPLETED

            logger.info(
                f"Workflow execution completed: {execution_id} "
                f"(status: {execution.status}, duration: {execution.total_duration_ms}ms)"
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {execution_id} - {e}")
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.total_duration_ms = int((time.monotonic() - start_time) * 1000)

        finally:
            self._active_executions.pop(execution_id, None)

        return execution

    async def _execute_step(
        self,
        step: Any,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        handler: LLMBackend | None = None,
    ) -> StepResult:
        """执行单个步骤
        
        Args:
            step: 步骤定义
            workflow: 工作流定义
            execution: 执行记录
            handler: LLM 处理器
        
        Returns:
            步骤执行结果
        """
        start_time = time.monotonic()
        started_at = datetime.now()

        logger.info(f"Executing step: {step.id} ({step.name})")

        # 构建输入
        input_params = self._build_step_input(step, workflow, execution)

        # 确定执行的 Agent
        agent_config = None
        if step.agent_id:
            agent_config = self.registry.get(step.agent_id)
        else:
            # 根据能力匹配 Agent
            matched = self.registry.match_by_capability([step.mode])
            if matched:
                agent_config = matched[0]

        result = StepResult(
            step_id=step.id,
            step_name=step.name,
            status=StepStatus.RUNNING,
            started_at=started_at,
            agent_id=agent_config.agent_id if agent_config else None,
            agent_name=agent_config.name if agent_config else None,
        )

        try:
            if agent_config:
                # 使用 Sub-Agent 执行
                executor = SubAgentExecutor(handler)

                for retry in range(step.retry_on_failure + 1):
                    sub_result = await asyncio.wait_for(
                        executor.execute(
                            agent_config=agent_config,
                            task_params={"input": str(input_params), "skills": step.skills},
                            llm_handler=handler,
                        ),
                        timeout=step.timeout,
                    )

                    if sub_result.status == SubAgentStatus.COMPLETED:
                        result.status = StepStatus.COMPLETED
                        result.output = sub_result.output
                        result.artifacts = sub_result.artifacts
                        result.token_usage = sub_result.token_usage
                        result.retry_count = retry
                        break

                    elif sub_result.status == SubAgentStatus.TIMEOUT:
                        logger.warning(f"Step {step.id} timeout (retry {retry}/{step.retry_on_failure})")
                        if retry == step.retry_on_failure:
                            result.status = StepStatus.TIMEOUT
                            result.error_message = f"Timeout after {step.timeout}s"

                    else:
                        logger.warning(f"Step {step.id} failed (retry {retry}/{step.retry_on_failure})")
                        if retry == step.retry_on_failure:
                            result.status = StepStatus.FAILED
                            result.error_message = sub_result.error_message

            else:
                # 使用 TaskRouter 执行（传统方式）
                from pm_workstation.chat.chat_models import TaskMode, TaskStatus

                try:
                    task_mode = TaskMode(step.mode.upper())
                except ValueError:
                    task_mode = None

                task_result = await asyncio.wait_for(
                    self.task_router.execute_task(
                        mode=task_mode,
                        params=input_params,
                        selected_skills=step.skills,
                    ),
                    timeout=step.timeout,
                )

                if task_result.status == TaskStatus.COMPLETED:
                    result.status = StepStatus.COMPLETED
                    result.output = task_result.output
                    result.artifacts = [
                        {"name": a.name, "url": a.url, "type": a.type}
                        for a in task_result.artifacts
                    ]
                else:
                    result.status = StepStatus.FAILED
                    result.error_message = task_result.error_message

        except TimeoutError:
            result.status = StepStatus.TIMEOUT
            result.error_message = f"Timeout after {step.timeout}s"

        except Exception as e:
            logger.error(f"Step {step.id} exception: {e}")
            result.status = StepStatus.FAILED
            result.error_message = str(e)

        result.completed_at = datetime.now()
        result.duration_ms = int((time.monotonic() - start_time) * 1000)

        return result

    def get_progress(self, execution_id: str) -> WorkflowProgress | None:
        """获取执行进度
        
        Args:
            execution_id: 执行 ID
        
        Returns:
            进度信息
        """
        execution = self._active_executions.get(execution_id)
        if not execution:
            return None

        completed_names = [
            r.step_name for r in execution.steps_results
            if r.status == StepStatus.COMPLETED
        ]
        running_names = [
            r.step_name for r in execution.steps_results
            if r.status == StepStatus.RUNNING
        ]
        pending_names = []
        failed_names = [
            r.step_name for r in execution.steps_results
            if r.status == StepStatus.FAILED
        ]

        progress_percent = (
            execution.completed_steps / execution.total_steps * 100
            if execution.total_steps > 0 else 0
        )

        current_step = None
        current_status = None
        if execution.steps_results:
            current_result = execution.steps_results[-1]
            if current_result.status == StepStatus.RUNNING:
                current_step = current_result.step_name
                current_status = current_result.status

        artifacts = []
        for r in execution.steps_results:
            if r.artifacts:
                artifacts.extend(r.artifacts)

        return WorkflowProgress(
            execution_id=execution_id,
            workflow_id=execution.workflow_id,
            workflow_name=execution.workflow_name,
            status=execution.status,
            progress_percent=progress_percent,
            current_step=current_step,
            current_step_status=current_status,
            completed_steps=completed_names,
            running_steps=running_names,
            pending_steps=pending_names,
            failed_steps=failed_names,
            artifacts_generated=artifacts,
        )


_global_orchestrator: WorkflowOrchestrator | None = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """获取全局工作流编排器"""
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = WorkflowOrchestrator()
    return _global_orchestrator


def reset_orchestrator() -> None:
    """重置编排器（用于测试）"""
    global _global_orchestrator
    _global_orchestrator = WorkflowOrchestrator()
