"""Sub-agent 注册表测试"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from pm_workstation.agents.registry import SubAgentConfig, SubAgentRegistry


class TestSubAgentConfig:
    """SubAgentConfig 测试"""

    def test_create_config(self):
        """测试创建配置"""
        config = SubAgentConfig(
            id="test-agent",
            name="测试 Agent",
            description="测试描述",
            system_prompt="你是测试专家",
        )

        assert config.id == "test-agent"
        assert config.name == "测试 Agent"
        assert config.tools == []
        assert config.skills == []
        assert config.model == "inherit"
        assert config.max_turns == 50
        assert config.timeout_seconds == 300

    def test_has_tool(self):
        """测试工具检查"""
        config = SubAgentConfig(
            id="test",
            name="Test",
            description="Test",
            system_prompt="Test",
            tools=["read_file", "write_file"],
        )

        assert config.has_tool("read_file") is True
        assert config.has_tool("write_file") is True
        assert config.has_tool("bash") is False

    def test_has_skill(self):
        """测试技能检查"""
        config = SubAgentConfig(
            id="test",
            name="Test",
            description="Test",
            system_prompt="Test",
            skills=["skill-a", "skill-b"],
        )

        assert config.has_skill("skill-a") is True
        assert config.has_skill("skill-c") is False

    def test_get_capabilities(self):
        """测试获取能力列表"""
        config = SubAgentConfig(
            id="test",
            name="Test",
            description="Test",
            system_prompt="Test",
            tools=["tool-a", "tool-b"],
            skills=["skill-a"],
        )

        caps = config.get_capabilities()
        assert set(caps) == {"tool-a", "tool-b", "skill-a"}


class TestSubAgentRegistry:
    """SubAgentRegistry 测试"""

    def test_register_agent(self):
        """测试注册 Agent"""
        registry = SubAgentRegistry()
        config = SubAgentConfig(
            id="test-agent",
            name="Test",
            description="Test",
            system_prompt="Test",
        )

        registry.register(config)
        assert "test-agent" in registry
        assert len(registry) == 1

    def test_register_duplicate_raises(self):
        """测试重复注册抛出异常"""
        registry = SubAgentRegistry()
        config = SubAgentConfig(
            id="test-agent",
            name="Test",
            description="Test",
            system_prompt="Test",
        )

        registry.register(config)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(config)

    def test_unregister_agent(self):
        """测试注销 Agent"""
        registry = SubAgentRegistry()
        config = SubAgentConfig(
            id="test-agent",
            name="Test",
            description="Test",
            system_prompt="Test",
        )

        registry.register(config)
        registry.unregister("test-agent")
        assert "test-agent" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_raises(self):
        """测试注销不存在的 Agent 抛出异常"""
        registry = SubAgentRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    def test_get_agent(self):
        """测试获取 Agent"""
        registry = SubAgentRegistry()
        config = SubAgentConfig(
            id="test-agent",
            name="Test",
            description="Test",
            system_prompt="Test",
        )

        registry.register(config)
        result = registry.get("test-agent")
        assert result is not None
        assert result.id == "test-agent"

    def test_get_nonexistent_returns_none(self):
        """测试获取不存在的 Agent 返回 None"""
        registry = SubAgentRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_list_all(self):
        """测试列出所有 Agent"""
        registry = SubAgentRegistry()
        for i in range(3):
            registry.register(SubAgentConfig(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                system_prompt="Test",
            ))

        agents = registry.list_all()
        assert len(agents) == 3

    def test_match_by_capability(self):
        """测试按能力匹配"""
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="analyst",
            name="Analyst",
            description="Test",
            system_prompt="Test",
            tools=["read_file", "write_file"],
            skills=["requirement-analysis"],
        ))
        registry.register(SubAgentConfig(
            id="designer",
            name="Designer",
            description="Test",
            system_prompt="Test",
            tools=["read_file", "str_replace"],
            skills=["prototype-generation"],
        ))

        # 匹配 read_file
        matches = registry.match_by_capability(["read_file"])
        assert len(matches) == 2
        assert matches[0].id in ("analyst", "designer")

        # 匹配 requirement-analysis
        matches = registry.match_by_capability(["requirement-analysis"])
        assert len(matches) == 1
        assert matches[0].id == "analyst"

        # 匹配不存在的技能
        matches = registry.match_by_capability(["nonexistent"])
        assert len(matches) == 0

    def test_match_by_capability_scores(self):
        """测试匹配度评分"""
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="full-stack",
            name="Full Stack",
            description="Test",
            system_prompt="Test",
            tools=["read_file", "write_file", "bash"],
            skills=["coding", "testing"],
        ))
        registry.register(SubAgentConfig(
            id="coder",
            name="Coder",
            description="Test",
            system_prompt="Test",
            tools=["read_file", "write_file"],
            skills=["coding"],
        ))

        # full-stack 匹配更多
        matches = registry.match_by_capability(["read_file", "bash", "coding"])
        assert len(matches) == 2
        assert matches[0].id == "full-stack"
        assert matches[1].id == "coder"

    def test_load_from_file(self):
        """测试从文件加载"""
        config_data = {
            "subagents": {
                "test-agent": {
                    "name": "Test",
                    "description": "Test",
                    "system_prompt": "Test",
                    "tools": ["read_file"],
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            registry = SubAgentRegistry(config_path)
            assert "test-agent" in registry
            agent = registry.get("test-agent")
            assert agent is not None
            assert agent.name == "Test"
            assert agent.tools == ["read_file"]
        finally:
            os.unlink(config_path)

    def test_load_from_nonexistent_file_raises(self):
        """测试从不存在的文件加载抛出异常"""
        with pytest.raises(FileNotFoundError):
            SubAgentRegistry("/nonexistent/path/config.yaml")

    def test_load_from_empty_file(self):
        """测试从空文件加载"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            registry = SubAgentRegistry(config_path)
            assert len(registry) == 0
        finally:
            os.unlink(config_path)

    def test_to_dict(self):
        """测试导出为字典"""
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="test-agent",
            name="Test",
            description="Test",
            system_prompt="Test",
            tools=["read_file"],
        ))

        result = registry.to_dict()
        assert "test-agent" in result
        assert result["test-agent"]["name"] == "Test"

    def test_repr(self):
        """测试字符串表示"""
        registry = SubAgentRegistry()
        registry.register(SubAgentConfig(
            id="agent-a",
            name="A",
            description="Test",
            system_prompt="Test",
        ))

        assert "agent-a" in repr(registry)

    def test_load_from_project_config(self):
        """测试从项目配置文件加载"""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "subagents.yaml"
        if config_path.exists():
            registry = SubAgentRegistry(str(config_path))
            # 验证加载了所有预期的 agent
            assert "analyst" in registry
            assert "writer" in registry
            assert "designer" in registry
            assert "reviewer" in registry
            assert "qa" in registry
            assert len(registry) == 5
