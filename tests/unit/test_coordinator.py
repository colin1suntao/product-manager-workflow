"""Coordinator Agent 测试"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.agents.coordinator import (
    COORDINATOR_SYSTEM_PROMPT,
    CoordinatorAgent,
)
from pm_workstation.agents.middlewares.base import MiddlewareChain
from pm_workstation.agents.registry import SubAgentConfig, SubAgentRegistry
from pm_workstation.agents.task_tool import (
    SubTask,
    TaskDecomposition,
    TaskDelegationTool,
    TaskResult,
)
from pm_workstation.model_router.base import LLMResponse


class TestCoordinatorAgent:
    """CoordinatorAgent 测试"""

    def _create_coordinator(
        self,
        llm_response: str = '{"plan": "test", "subtasks": [], "execution_order": []}',
        subagent_configs: list[SubAgentConfig] | None = None,
    ) -> CoordinatorAgent:
        """创建 Coordinator 实例"""
        # Mock LLM Handler
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = LLMResponse(
            content=llm_response,
            model="gpt-4",
        )

        # Mock Registry
        registry = SubAgentRegistry()
        if subagent_configs:
            for config in subagent_configs:
                registry.register(config)
        else:
            # 注册默认的 5 个 agent
            for agent_id, name, desc in [
                ("analyst", "需求分析师", "分析需求"),
                ("writer", "PRD 写手", "生成 PRD"),
                ("designer", "原型设计师", "设计原型"),
                ("reviewer", "文档审阅员", "审阅文档"),
                ("qa", "校验员", "校验一致性"),
            ]:
                registry.register(SubAgentConfig(
                    id=agent_id,
                    name=name,
                    description=desc,
                    system_prompt=f"你是{name}",
                ))

        # Mock Task Tool
        mock_tool = AsyncMock(spec=TaskDelegationTool)
        mock_tool.invoke.return_value = TaskResult(
            task_id="task-1",
            agent_id="analyst",
            status="success",
            output="分析完成",
            duration=1.0,
        )
        mock_tool.invoke_batch.return_value = [
            TaskResult(
                task_id="task-1",
                agent_id="analyst",
                status="success",
                output="结果 1",
                duration=1.0,
            ),
            TaskResult(
                task_id="task-2",
                agent_id="writer",
                status="success",
                output="结果 2",
                duration=1.5,
            ),
        ]

        middleware_chain = MiddlewareChain()

        return CoordinatorAgent(
            llm_handler=mock_llm,
            registry=registry,
            task_tool=mock_tool,
            middleware_chain=middleware_chain,
        )

    @pytest.mark.asyncio
    async def test_process_request_success(self):
        """测试处理请求成功"""
        llm_response = json.dumps({
            "plan": "分析并生成",
            "subtasks": [
                {
                    "id": "task-1",
                    "agent_id": "analyst",
                    "description": "分析需求",
                    "expected_output": "分析结果",
                    "timeout": 180,
                    "can_run_parallel": True,
                }
            ],
            "execution_order": ["task-1"],
        })

        coordinator = self._create_coordinator(llm_response=llm_response)
        # 覆盖 batch 返回值匹配 1 个任务
        coordinator.task_tool.invoke_batch.return_value = [
            TaskResult(
                task_id="task-1",
                agent_id="analyst",
                status="success",
                output="分析完成",
                duration=1.0,
            ),
        ]

        result = await coordinator.process_request("我需要创建一个用户管理系统")

        assert "plan" in result
        assert "results" in result
        assert "summary" in result
        assert result["total_subtasks"] == 1
        assert result["successful_subtasks"] == 1
        assert result["duration"] >= 0

    @pytest.mark.asyncio
    async def test_process_request_with_multiple_tasks(self):
        """测试处理多个子任务"""
        llm_response = json.dumps({
            "plan": "完整工作流",
            "subtasks": [
                {
                    "id": "task-1",
                    "agent_id": "analyst",
                    "description": "分析需求",
                    "timeout": 180,
                    "can_run_parallel": True,
                },
                {
                    "id": "task-2",
                    "agent_id": "writer",
                    "description": "生成 PRD",
                    "timeout": 240,
                    "can_run_parallel": True,
                },
                {
                    "id": "task-3",
                    "agent_id": "designer",
                    "description": "设计原型",
                    "timeout": 300,
                    "can_run_parallel": True,
                },
            ],
            "execution_order": ["task-1", "task-2", "task-3"],
        })

        coordinator = self._create_coordinator(
            llm_response=llm_response,
        )

        # 覆盖 invoke_batch 返回 3 个结果
        coordinator.task_tool.invoke_batch.return_value = [
            TaskResult(task_id="task-1", agent_id="analyst", status="success", output="分析", duration=1.0),
            TaskResult(task_id="task-2", agent_id="writer", status="success", output="PRD", duration=1.5),
            TaskResult(task_id="task-3", agent_id="designer", status="success", output="原型", duration=2.0),
        ]

        result = await coordinator.process_request("创建用户管理系统")

        assert result["total_subtasks"] == 3
        assert result["successful_subtasks"] == 3

    def test_build_system_prompt(self):
        """测试构建系统提示"""
        coordinator = self._create_coordinator()
        prompt = coordinator.system_prompt

        assert "协调员" in prompt
        assert "analyst" in prompt
        assert "writer" in prompt
        assert "designer" in prompt

    def test_get_agent_descriptions(self):
        """测试获取 Agent 描述"""
        coordinator = self._create_coordinator()
        descriptions = coordinator._get_agent_descriptions()

        assert "需求分析师" in descriptions
        assert "PRD 写手" in descriptions
        assert "原型设计师" in descriptions

    def test_build_decomposition_prompt(self):
        """测试构建分解提示"""
        coordinator = self._create_coordinator()
        prompt = coordinator._build_decomposition_prompt("测试需求")

        assert "测试需求" in prompt
        assert "拆解" in prompt

    def test_parse_decomposition_response(self):
        """测试解析分解响应"""
        coordinator = self._create_coordinator()
        content = '''```json
{
  "plan": "分析需求",
  "subtasks": [
    {
      "id": "task-1",
      "agent_id": "analyst",
      "description": "分析需求",
      "timeout": 180,
      "can_run_parallel": true
    }
  ],
  "execution_order": ["task-1"]
}
```'''

        result = coordinator._parse_decomposition_response(content)
        assert result.plan == "分析需求"
        assert len(result.subtasks) == 1
        assert result.subtasks[0].id == "task-1"
        assert result.execution_order == ["task-1"]

    def test_parse_decomposition_response_without_code_block(self):
        """测试解析无代码块的响应"""
        coordinator = self._create_coordinator()
        content = json.dumps({
            "plan": "简单计划",
            "subtasks": [],
            "execution_order": [],
        })

        result = coordinator._parse_decomposition_response(content)
        assert result.plan == "简单计划"
        assert len(result.subtasks) == 0

    def test_extract_json_from_code_block(self):
        """测试从代码块提取 JSON"""
        json_str = CoordinatorAgent._extract_json(
            '```json\n{"key": "value"}\n```'
        )
        assert json_str == '{"key": "value"}'

    def test_extract_json_direct(self):
        """测试直接提取 JSON"""
        json_str = CoordinatorAgent._extract_json('{"key": "value"}')
        assert json_str == '{"key": "value"}'

    def test_extract_json_returns_none(self):
        """测试无法提取 JSON 时返回 None"""
        result = CoordinatorAgent._extract_json("这不是 JSON")
        assert result is None

    @pytest.mark.asyncio
    async def test_decompose_task_llm_failure_uses_default(self):
        """测试 LLM 分解失败时使用默认计划"""
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM API error")

        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="analyst",
            name="分析师",
            description="分析",
            system_prompt="Test",
        ))
        registry.register(SubAgentConfig(
            id="writer",
            name="写手",
            description="写作",
            system_prompt="Test",
        ))
        registry.register(SubAgentConfig(
            id="designer",
            name="设计师",
            description="设计",
            system_prompt="Test",
        ))

        mock_tool = AsyncMock(spec=TaskDelegationTool)
        coordinator = CoordinatorAgent(
            llm_handler=mock_llm,
            registry=registry,
            task_tool=mock_tool,
        )

        decomposition = await coordinator._decompose_task("测试需求")
        assert decomposition.plan is not None
        assert len(decomposition.subtasks) > 0

    def test_create_default_decomposition(self):
        """测试创建默认分解"""
        coordinator = self._create_coordinator()
        decomp = coordinator._create_default_decomposition("用户需求文本")

        assert decomp.plan is not None
        assert len(decomp.subtasks) >= 3
        # 第一个任务不可并行（顺序依赖）
        assert decomp.subtasks[0].can_run_parallel is False
        # 后续任务可并行
        assert decomp.subtasks[1].can_run_parallel is True

    @pytest.mark.asyncio
    async def test_delegate_and_collect_parallel(self):
        """测试并行委派和收集"""
        decomposition = TaskDecomposition(
            plan="并行执行",
            subtasks=[
                SubTask(
                    id="task-1",
                    agent_id="analyst",
                    description="分析",
                    can_run_parallel=True,
                ),
                SubTask(
                    id="task-2",
                    agent_id="writer",
                    description="写作",
                    can_run_parallel=True,
                ),
            ],
            execution_order=["task-1", "task-2"],
        )

        coordinator = self._create_coordinator()
        results = await coordinator._delegate_and_collect(decomposition)

        coordinator.task_tool.invoke_batch.assert_called_once()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delegate_and_collect_sequential(self):
        """测试顺序委派和收集"""
        decomposition = TaskDecomposition(
            plan="顺序执行",
            subtasks=[
                SubTask(
                    id="task-1",
                    agent_id="analyst",
                    description="分析",
                    can_run_parallel=False,
                ),
            ],
            execution_order=["task-1"],
        )

        coordinator = self._create_coordinator()
        results = await coordinator._delegate_and_collect(decomposition)

        coordinator.task_tool.invoke.assert_called_once()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_summarize_results(self):
        """测试汇总结果"""
        decomposition = TaskDecomposition(
            plan="测试计划",
            subtasks=[
                SubTask(
                    id="task-1",
                    agent_id="analyst",
                    description="分析需求",
                ),
                SubTask(
                    id="task-2",
                    agent_id="writer",
                    description="生成 PRD",
                ),
            ],
            execution_order=["task-1", "task-2"],
        )

        results = {
            "task-1": TaskResult(
                task_id="task-1",
                agent_id="analyst",
                status="success",
                output="分析完成",
                duration=1.0,
            ),
            "task-2": TaskResult(
                task_id="task-2",
                agent_id="writer",
                status="failed",
                error="超时",
                duration=5.0,
            ),
        }

        coordinator = self._create_coordinator()
        summary = await coordinator._summarize_results(decomposition, results)

        assert "测试计划" in summary
        assert "分析需求" in summary
        assert "生成 PRD" in summary
        assert "1 个失败" in summary

    @pytest.mark.asyncio
    async def test_summarize_results_missing_result(self):
        """测试汇总缺少结果"""
        decomposition = TaskDecomposition(
            plan="计划",
            subtasks=[
                SubTask(id="task-1", agent_id="analyst", description="任务 1"),
                SubTask(id="task-2", agent_id="writer", description="任务 2"),
            ],
            execution_order=["task-1", "task-2"],
        )

        # 只有 task-1 有结果
        results = {
            "task-1": TaskResult(
                task_id="task-1",
                agent_id="analyst",
                status="success",
                output="完成",
            ),
        }

        coordinator = self._create_coordinator()
        summary = await coordinator._summarize_results(decomposition, results)

        assert "未执行" in summary
