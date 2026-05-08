"""Sub-agent 注册表模块

实现 Sub-agent 配置管理和动态注册/注销功能。
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SubAgentConfig(BaseModel):
    """Sub-agent 配置模型"""

    id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    model: str = "inherit"  # inherit/use_default/specific_model
    max_turns: int = 50
    timeout_seconds: int = 300

    def has_tool(self, tool_name: str) -> bool:
        """检查是否拥有指定工具"""
        return tool_name in self.tools

    def has_skill(self, skill_name: str) -> bool:
        """检查是否拥有指定技能"""
        return skill_name in self.skills

    def get_capabilities(self) -> list[str]:
        """获取所有能力列表"""
        return self.tools + self.skills


class SubAgentRegistry:
    """Sub-agent 注册表

    管理所有已注册的 Sub-agent，支持从配置文件加载和动态注册。
    """

    def __init__(self, config_path: str | None = None):
        self._agents: dict[str, SubAgentConfig] = {}
        if config_path:
            self.load_from_file(config_path)

    def register(self, config: SubAgentConfig) -> None:
        """注册一个 Sub-agent

        Args:
            config: Sub-agent 配置

        Raises:
            ValueError: 如果 agent id 已存在
        """
        if config.id in self._agents:
            raise ValueError(f"Sub-agent '{config.id}' already registered")
        self._agents[config.id] = config

    def unregister(self, agent_id: str) -> None:
        """注销一个 Sub-agent

        Args:
            agent_id: Agent ID

        Raises:
            KeyError: 如果 agent id 不存在
        """
        if agent_id not in self._agents:
            raise KeyError(f"Sub-agent '{agent_id}' not found")
        del self._agents[agent_id]

    def get(self, agent_id: str) -> SubAgentConfig | None:
        """获取指定 Agent 的配置

        Args:
            agent_id: Agent ID

        Returns:
            Sub-agent 配置，如果不存在返回 None
        """
        return self._agents.get(agent_id)

    def list_all(self) -> list[SubAgentConfig]:
        """列出所有已注册的 Sub-agent

        Returns:
            所有 Sub-agent 配置列表
        """
        return list(self._agents.values())

    def match_by_capability(self, required_capabilities: list[str]) -> list[SubAgentConfig]:
        """根据能力需求匹配 Sub-agent

        Args:
            required_capabilities: 需要的能力列表

        Returns:
            匹配的 Sub-agent 列表，按匹配度降序排列
        """
        if not required_capabilities:
            return []

        matches = []
        required_set = set(required_capabilities)

        for agent in self._agents.values():
            agent_capabilities = set(agent.get_capabilities())
            matched = required_set & agent_capabilities
            if matched:
                # 匹配度 = 匹配的能力数 / 需要的能力数
                match_score = len(matched) / len(required_set)
                matches.append((match_score, agent))

        # 按匹配度降序排列
        matches.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in matches]

    def load_from_file(self, config_path: str) -> None:
        """从 YAML 配置文件加载 Sub-agent 配置

        Args:
            config_path: 配置文件路径

        Raises:
            FileNotFoundError: 如果配置文件不存在
            yaml.YAMLError: 如果 YAML 解析失败
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "subagents" not in data:
            return

        for agent_id, agent_data in data["subagents"].items():
            config = SubAgentConfig(id=agent_id, **agent_data)
            self._agents[agent_id] = config

    def to_dict(self) -> dict[str, Any]:
        """导出注册表为字典

        Returns:
            注册表字典
        """
        return {
            agent_id: config.model_dump()
            for agent_id, config in self._agents.items()
        }

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"SubAgentRegistry(agents={list(self._agents.keys())})"
