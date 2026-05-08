"""Phase 3 集成测试：Sub-agent 迁移和技能加载"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from pm_workstation.agents.registry import SubAgentConfig, SubAgentRegistry
from pm_workstation.agents.task_tool import (
    ContextManager,
    SubAgentExecutor,
    TaskDelegationTool,
    TaskRequest,
    TaskResult,
)
from pm_workstation.model_router.base import LLMResponse
from pm_workstation.skills.loader import SkillLoader


class TestSubAgentWithSkills:
    """Sub-agent 与技能集成测试"""

    def _create_skill_dir(self, skills: dict) -> str:
        """创建临时技能目录"""
        tmpdir = tempfile.mkdtemp()
        for name, data in skills.items():
            file_path = Path(tmpdir) / f"{name}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f)
        return tmpdir

    @pytest.mark.asyncio
    async def test_executor_loads_skills(self):
        """测试执行器加载技能"""
        skills_data = {
            "test-skill": {
                "name": "test-skill",
                "description": "测试技能",
                "system_prompt": "技能系统提示",
                "tools": ["read_file"],
                "steps": ["步骤 1"],
            }
        }
        tmpdir = self._create_skill_dir(skills_data)
        try:
            skill_loader = SkillLoader(skills_dir=tmpdir)

            mock_handler = AsyncMock()
            mock_handler.chat.return_value = LLMResponse(
                content="执行结果",
                model="gpt-4",
            )
            mock_factory = MagicMock()
            mock_factory.get_default.return_value = mock_handler

            executor = SubAgentExecutor(
                llm_factory=mock_factory,
                skill_loader=skill_loader,
            )

            config = SubAgentConfig(
                id="test-agent",
                name="测试",
                description="测试",
                system_prompt="基础提示",
                skills=["test-skill"],
            )

            result = await executor.execute(
                config=config,
                task="执行任务",
                context={},
            )

            # 验证 LLM 被调用
            mock_handler.chat.assert_called_once()
            messages = mock_handler.chat.call_args[0][0]

            # 验证系统提示包含技能信息
            system_prompt = messages[0].content
            assert "基础提示" in system_prompt
            assert "技能系统提示" in system_prompt
            assert "步骤 1" in system_prompt

            assert result == "执行结果"
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    @pytest.mark.asyncio
    async def test_executor_with_multiple_skills(self):
        """测试执行器加载多个技能"""
        skills_data = {
            "skill-a": {
                "name": "skill-a",
                "description": "技能 A",
                "system_prompt": "技能 A 提示",
            },
            "skill-b": {
                "name": "skill-b",
                "description": "技能 B",
                "system_prompt": "技能 B 提示",
            },
        }
        tmpdir = self._create_skill_dir(skills_data)
        try:
            skill_loader = SkillLoader(skills_dir=tmpdir)

            mock_handler = AsyncMock()
            mock_handler.chat.return_value = LLMResponse(
                content="结果",
                model="gpt-4",
            )
            mock_factory = MagicMock()
            mock_factory.get_default.return_value = mock_handler

            executor = SubAgentExecutor(
                llm_factory=mock_factory,
                skill_loader=skill_loader,
            )

            config = SubAgentConfig(
                id="test",
                name="测试",
                description="测试",
                system_prompt="基础",
                skills=["skill-a", "skill-b"],
            )

            await executor.execute(
                config=config,
                task="任务",
                context={},
            )

            messages = mock_handler.chat.call_args[0][0]
            system_prompt = messages[0].content
            assert "技能 A 提示" in system_prompt
            assert "技能 B 提示" in system_prompt
        finally:
            for f in Path(tmpdir).glob("*.yaml"):
                f.unlink()
            Path(tmpdir).rmdir()

    @pytest.mark.asyncio
    async def test_executor_with_nonexistent_skill(self):
        """测试执行器处理不存在的技能"""
        mock_handler = AsyncMock()
        mock_handler.chat.return_value = LLMResponse(
            content="结果",
            model="gpt-4",
        )
        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(
            llm_factory=mock_factory,
            skill_loader=SkillLoader(),  # 空技能加载器
        )

        config = SubAgentConfig(
            id="test",
            name="测试",
            description="测试",
            system_prompt="基础",
            skills=["nonexistent-skill"],
        )

        # 不应该抛出异常
        result = await executor.execute(
            config=config,
            task="任务",
            context={},
        )
        assert result == "结果"

    @pytest.mark.asyncio
    async def test_tool_whitelist_filtering(self):
        """测试工具白名单过滤"""
        config = SubAgentConfig(
            id="analyst",
            name="分析师",
            description="分析",
            system_prompt="你是分析师",
            tools=["read_file", "write_file"],
        )

        assert config.has_tool("read_file") is True
        assert config.has_tool("bash") is False
        assert config.has_tool("write_file") is True


class TestRegistryWithConfigFile:
    """注册表与配置文件集成测试"""

    def test_load_subagents_from_config(self):
        """测试从配置文件加载 sub-agents"""
        config_path = Path(__file__).parent.parent.parent / "config" / "subagents.yaml"
        if config_path.exists():
            registry = SubAgentRegistry(str(config_path))

            assert len(registry) == 5
            assert "analyst" in registry
            assert "writer" in registry
            assert "designer" in registry
            assert "reviewer" in registry
            assert "qa" in registry

            analyst = registry.get("analyst")
            assert analyst is not None
            assert analyst.name == "需求分析师"
            assert "requirement-analysis" in analyst.skills

    def test_registry_agent_descriptions(self):
        """测试注册表 Agent 描述"""
        config_path = Path(__file__).parent.parent.parent / "config" / "subagents.yaml"
        if config_path.exists():
            registry = SubAgentRegistry(str(config_path))
            agents = registry.list_all()

            for agent in agents:
                assert agent.description != ""
                assert agent.system_prompt != ""
                assert len(agent.skills) > 0


class TestEndToEndSubAgentExecution:
    """端到端子 Agent 执行测试"""

    @pytest.mark.asyncio
    async def test_full_delegation_flow(self):
        """测试完整的委派流程"""
        # 1. 创建注册表
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="analyst",
            name="分析师",
            description="分析",
            system_prompt="你是分析师",
            skills=["requirement-analysis"],
            timeout_seconds=60,
        ))

        # 2. 创建执行器（空技能）
        mock_handler = AsyncMock()
        mock_handler.chat.return_value = LLMResponse(
            content="分析完成",
            model="gpt-4",
        )
        mock_factory = MagicMock()
        mock_factory.get_default.return_value = mock_handler

        executor = SubAgentExecutor(
            llm_factory=mock_factory,
            context_manager=ContextManager(),
        )

        # 3. 创建委派工具
        tool = TaskDelegationTool(
            registry=registry,
            executor=executor,
        )

        # 4. 委派任务
        result = await tool.invoke(
            agent_id="analyst",
            task_description="分析用户需求",
        )

        # 5. 验证结果
        assert result.status == "success"
        assert result.output == "分析完成"
        assert result.agent_id == "analyst"
