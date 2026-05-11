"""Coordinator Agent - 工作流协调员

核心编排 Agent，负责理解用户需求、拆解任务、委派给子 Agent、汇总结果。
"""

import json
import logging
import re
import time
from typing import Any

from pm_workstation.agents.middlewares.base import MiddlewareChain
from pm_workstation.agents.registry import SubAgentRegistry
from pm_workstation.agents.task_tool import (
    SubTask,
    TaskDecomposition,
    TaskDelegationTool,
    TaskRequest,
    TaskResult,
)
from pm_workstation.model_router.base import LLMBackend, LLMMessage

logger = logging.getLogger(__name__)

# 系统提示模板
COORDINATOR_SYSTEM_PROMPT = """你是产品经理工作站的协调员。你的职责是：

1. 理解用户需求并拆解为可执行的子任务
2. 选择合适的子 Agent 执行每个子任务
3. 监控进度并处理异常
4. 汇总所有结果并交付给用户

## 可用的子 Agent

{agent_descriptions}

## 任务拆解规则

- 每个子任务应该明确、独立、可执行
- 优先并行执行不依赖的子任务
- 每个子任务指定合适的 agent_id
- 最多同时委派 3 个子任务

## 输出格式

拆解任务时，输出 JSON 格式：
```json
{{
  "plan": "执行计划描述",
  "subtasks": [
    {{
      "id": "task-1",
      "agent_id": "analyst",
      "description": "任务描述",
      "expected_output": "期望输出",
      "timeout": 180,
      "can_run_parallel": true
    }}
  ],
  "execution_order": ["task-1", "task-2", "task-3"]
}}
```"""


class CoordinatorAgent:
    """协调员 Agent

    工作流编排的核心 Agent，负责任务拆解、委派、汇总。
    """

    def __init__(
        self,
        llm_handler: LLMBackend,
        registry: SubAgentRegistry,
        task_tool: TaskDelegationTool,
        middleware_chain: MiddlewareChain | None = None,
    ):
        self.llm_handler = llm_handler
        self.registry = registry
        self.task_tool = task_tool
        self.middleware_chain = middleware_chain or MiddlewareChain()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        agent_descriptions = self._get_agent_descriptions()
        return COORDINATOR_SYSTEM_PROMPT.format(
            agent_descriptions=agent_descriptions,
        )

    def _get_agent_descriptions(self) -> str:
        """获取所有已注册 Agent 的描述"""
        agents = self.registry.list_all()
        if not agents:
            return "（暂无可用的子 Agent）"

        lines = []
        for agent in agents:
            lines.append(f"- **{agent.id}** ({agent.name}): {agent.description}")
            if agent.skills:
                lines.append(f"  技能: {', '.join(agent.skills)}")
        return "\n".join(lines)

    async def process_request(
        self,
        requirement_text: str,
        state: dict[str, Any] | None = None,
        selected_skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """处理用户请求

        完整流程：拆解任务 -> 委派执行 -> 汇总结果

        Args:
            requirement_text: 用户需求文本
            state: 可选的额外状态数据
            selected_skills: 用户选择的 PM Skills 技能名称列表

        Returns:
            处理结果字典
        """
        start_time = time.monotonic()

        # 步骤 1: 拆解任务（传入技能信息）
        decomposition = await self._decompose_task(requirement_text, selected_skills=selected_skills)
        logger.info(
            f"Task decomposed: {len(decomposition.subtasks)} subtasks"
        )

        # 步骤 2: 委派并收集结果（传入技能信息）
        results = await self._delegate_and_collect(decomposition, selected_skills=selected_skills)

        # 步骤 3: 汇总结果
        summary = await self._summarize_results(decomposition, results)

        elapsed = time.monotonic() - start_time

        return {
            "plan": decomposition.plan,
            "subtasks": decomposition.subtasks,
            "execution_order": decomposition.execution_order,
            "results": results,
            "summary": summary,
            "duration": elapsed,
            "total_subtasks": len(decomposition.subtasks),
            "successful_subtasks": sum(
                1 for r in results.values() if r.status == "success"
            ),
            "failed_subtasks": sum(
                1 for r in results.values() if r.status != "success"
            ),
        }

    async def _decompose_task(
        self,
        requirement_text: str,
        selected_skills: list[str] | None = None,
    ) -> TaskDecomposition:
        """拆解任务

        使用 LLM 分析需求并生成任务分解计划。

        Args:
            requirement_text: 用户需求文本
            selected_skills: 用户选择的 PM Skills 技能名称列表

        Returns:
            任务拆解结果
        """
        prompt = self._build_decomposition_prompt(requirement_text, selected_skills=selected_skills)

        try:
            response = await self.llm_handler.chat([
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=prompt),
            ])

            return self._parse_decomposition_response(response.content)
        except Exception as e:
            logger.warning(f"LLM decomposition failed: {e}, using default plan")
            return self._create_default_decomposition(requirement_text, selected_skills=selected_skills)

    def _build_decomposition_prompt(self, requirement_text: str, selected_skills: list[str] | None = None) -> str:
        """构建任务拆解提示"""
        prompt = f"""请分析以下需求并拆解为可执行的子任务：

## 需求描述

{requirement_text}

## 要求

1. 根据需求类型选择合适的子 Agent
2. 每个子任务应该有明确的描述和期望输出
3. 标记可以并行执行的子任务
4. 指定合理的执行顺序
"""

        if selected_skills:
            skills_text = "\n".join([f"- {s}" for s in selected_skills])
            prompt += f"""
## 用户已选择的 PM Skills

用户在需求输入时选择了以下 PM Skills，请在任务拆解时充分利用这些技能：
{skills_text}
"""

        prompt += """
请输出 JSON 格式的任务分解计划。"""

        return prompt

    def _parse_decomposition_response(self, content: str) -> TaskDecomposition:
        """解析任务拆解响应

        Args:
            content: LLM 响应内容

        Returns:
            任务拆解结果
        """
        json_str = self._extract_json(content)
        if not json_str:
            raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        subtasks = []
        for task_data in data.get("subtasks", []):
            subtasks.append(SubTask(**task_data))

        return TaskDecomposition(
            plan=data.get("plan", "执行任务"),
            subtasks=subtasks,
            execution_order=data.get("execution_order", [t.id for t in subtasks]),
        )

    def _create_default_decomposition(
        self,
        requirement_text: str,
        selected_skills: list[str] | None = None,
    ) -> TaskDecomposition:
        """创建默认任务分解

        当 LLM 拆解失败时使用。

        Args:
            requirement_text: 用户需求文本
            selected_skills: 用户选择的 PM Skills 技能名称列表

        Returns:
            默认任务拆解
        """
        skills_suffix = ""
        if selected_skills:
            skills_suffix = f"\n\n用户选择的技能: {', '.join(selected_skills)}"

        subtasks = [
            SubTask(
                id="task-analyze",
                agent_id="analyst",
                description=f"分析需求: {requirement_text[:100]}...{skills_suffix}",
                expected_output="结构化需求分析",
                timeout=180,
                can_run_parallel=False,
            ),
            SubTask(
                id="task-prd",
                agent_id="writer",
                description=f"生成 PRD 文档{skills_suffix}",
                expected_output="PRD Markdown 文档",
                timeout=240,
                can_run_parallel=True,
            ),
            SubTask(
                id="task-prototype",
                agent_id="designer",
                description=f"设计原型{skills_suffix}",
                expected_output="HTML 原型",
                timeout=300,
                can_run_parallel=True,
            ),
        ]

        return TaskDecomposition(
            plan="默认任务分解：分析 -> 生成 PRD + 原型",
            subtasks=subtasks,
            execution_order=["task-analyze", "task-prd", "task-prototype"],
        )

    async def _delegate_and_collect(
        self,
        decomposition: TaskDecomposition,
        selected_skills: list[str] | None = None,
    ) -> dict[str, TaskResult]:
        """委派子任务并收集结果

        支持并发执行，最多 3 个子任务并行。

        Args:
            decomposition: 任务拆解结果
            selected_skills: 用户选择的 PM Skills 技能名称列表

        Returns:
            子任务结果映射 {task_id: TaskResult}
        """
        results: dict[str, TaskResult] = {}

        # 按执行顺序分组（考虑并行依赖）
        task_map = {t.id: t for t in decomposition.subtasks}

        # 找出可并行的任务
        parallel_tasks = []
        sequential_tasks = []

        for task_id in decomposition.execution_order:
            task = task_map.get(task_id)
            if task and task.can_run_parallel:
                parallel_tasks.append(task)
            else:
                sequential_tasks.append(task)

        # 并行执行可并行的任务
        if parallel_tasks:
            task_requests = [
                TaskRequest(
                    agent_id=task.agent_id,
                    task_description=task.description,
                    timeout=task.timeout,
                    user_skills=selected_skills,
                )
                for task in parallel_tasks
            ]

            parallel_results = await self.task_tool.invoke_batch(task_requests)
            for result in parallel_results:
                results[result.task_id] = result

        # 顺序执行不可并行的任务
        for task in sequential_tasks:
            result = await self.task_tool.invoke(
                agent_id=task.agent_id,
                task_description=task.description,
                timeout=task.timeout,
                user_skills=selected_skills,
            )
            results[result.task_id] = result

        return results

    async def _summarize_results(
        self,
        decomposition: TaskDecomposition,
        results: dict[str, TaskResult],
    ) -> str:
        """汇总子任务结果

        将多个子任务的结果合并为一份完整的摘要。

        Args:
            decomposition: 任务拆解
            results: 子任务结果映射

        Returns:
            汇总摘要
        """
        sections = []

        # 执行计划
        sections.append(f"## 执行计划\n\n{decomposition.plan}\n")

        # 各子任务结果
        sections.append("## 子任务执行结果\n")

        for task in decomposition.subtasks:
            result = results.get(task.id)
            if result:
                status_icon = "✅" if result.status == "success" else "❌"
                section = f"### {status_icon} {task.description}\n\n"
                section += f"- **Agent**: {task.agent_id}\n"
                section += f"- **状态**: {result.status}\n"
                section += f"- **耗时**: {result.duration:.2f}s\n"

                if result.output:
                    section += f"\n**输出**:\n\n{result.output[:500]}\n"
                    if len(result.output) > 500:
                        section += "\n*（输出已截断）*\n"
                elif result.error:
                    section += f"\n**错误**: {result.error}\n"

                sections.append(section)
            else:
                sections.append(f"### ⏭️ {task.description}\n\n*未执行*\n")

        # 总结
        successful = sum(1 for r in results.values() if r.status == "success")
        total = len(results)
        sections.append(
            f"\n## 总结\n\n"
            f"共 {total} 个子任务，{successful} 个成功，"
            f"{total - successful} 个失败。"
        )

        return "\n".join(sections)

    @staticmethod
    def _extract_json(content: str) -> str | None:
        """从文本中提取 JSON

        Args:
            content: 文本内容

        Returns:
            JSON 字符串，如果未找到返回 None
        """
        # 尝试匹配 ```json ... ``` 代码块
        json_match = re.search(r"```json\s*([\s\S]*?)```", content)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配 ``` ... ``` 代码块
        code_match = re.search(r"```\s*([\s\S]*?)```", content)
        if code_match:
            text = code_match.group(1).strip()
            if text.startswith("{"):
                return text

        # 尝试直接查找 JSON 对象
        if content.strip().startswith("{"):
            return content.strip()

        return None
