"""Sub-Agent Registry - Sub-Agent 注册表

管理所有已注册的 Sub-Agent，支持动态注册、注销和能力匹配。
"""

import logging
from datetime import datetime
from typing import Optional

from .sub_agent_models import (
    SubAgentConfig,
    SubAgentMatch,
    SubAgentRegistryStats,
)

logger = logging.getLogger(__name__)


class SubAgentRegistry:
    """Sub-Agent 注册表
    
    管理所有已注册的 Sub-Agent，支持：
    - 动态注册/注销
    - 能力匹配
    - 配置管理
    - 统计分析
    """
    
    def __init__(self):
        """初始化注册表"""
        self._agents: dict[str, SubAgentConfig] = {}
        self._capability_index: dict[str, list[str]] = {}  # capability -> agent_ids
        logger.info("SubAgentRegistry initialized")
    
    def register(self, config: SubAgentConfig) -> None:
        """注册 Sub-Agent
        
        Args:
            config: Sub-Agent 配置
        
        Raises:
            ValueError: 如果 agent_id 已存在
        """
        if config.agent_id in self._agents:
            logger.warning(f"Sub-Agent {config.agent_id} already exists, updating")
        
        self._agents[config.agent_id] = config
        
        # 更新能力索引
        for capability in config.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if config.agent_id not in self._capability_index[capability]:
                self._capability_index[capability].append(config.agent_id)
        
        logger.info(f"Registered Sub-Agent: {config.agent_id} ({config.name})")
    
    def unregister(self, agent_id: str) -> bool:
        """注销 Sub-Agent
        
        Args:
            agent_id: Agent ID
        
        Returns:
            是否成功注销
        """
        if agent_id not in self._agents:
            logger.warning(f"Sub-Agent {agent_id} not found")
            return False
        
        config = self._agents.pop(agent_id)
        
        # 更新能力索引
        for capability in config.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability] = [
                    aid for aid in self._capability_index[capability]
                    if aid != agent_id
                ]
        
        logger.info(f"Unregistered Sub-Agent: {agent_id}")
        return True
    
    def get(self, agent_id: str) -> Optional[SubAgentConfig]:
        """获取 Sub-Agent 配置
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Sub-Agent 配置，如果不存在返回 None
        """
        return self._agents.get(agent_id)
    
    def get_by_name(self, name: str) -> Optional[SubAgentConfig]:
        """根据名称获取 Sub-Agent
        
        Args:
            name: 显示名称
        
        Returns:
            Sub-Agent 配置
        """
        for config in self._agents.values():
            if config.name == name:
                return config
        return None
    
    def match_by_capability(self, capability: str) -> list[SubAgentConfig]:
        """根据能力匹配 Sub-Agent
        
        Args:
            capability: 能力标签
        
        Returns:
            匹配的 Sub-Agent 列表（按优先级排序）
        """
        agent_ids = self._capability_index.get(capability, [])
        agents = [
            self._agents[aid]
            for aid in agent_ids
            if aid in self._agents and self._agents[aid].enabled
        ]
        
        # 按优先级排序（高优先级在前）
        agents.sort(key=lambda a: a.priority, reverse=True)
        
        logger.debug(f"Matched {len(agents)} agents for capability: {capability}")
        return agents
    
    def match_by_capabilities(
        self,
        capabilities: list[str],
        min_match_score: float = 0.3,
    ) -> list[SubAgentMatch]:
        """根据多个能力匹配 Sub-Agent
        
        Args:
            capabilities: 能力标签列表
            min_match_score: 最小匹配分数
        
        Returns:
            匹配结果列表（按匹配分数排序）
        """
        matches: dict[str, SubAgentMatch] = {}
        
        for capability in capabilities:
            matched_agents = self.match_by_capability(capability)
            for agent in matched_agents:
                if agent.agent_id not in matches:
                    matches[agent.agent_id] = SubAgentMatch(
                        agent_id=agent.agent_id,
                        name=agent.name,
                        capabilities=agent.capabilities,
                        match_score=0.0,
                        matched_capabilities=[],
                    )
                
                matches[agent.agent_id].matched_capabilities.append(capability)
        
        # 计算匹配分数
        total_capabilities = len(capabilities)
        for match in matches.values():
            match.match_score = len(match.matched_capabilities) / total_capabilities
        
        # 过滤和排序
        valid_matches = [
            m for m in matches.values()
            if m.match_score >= min_match_score
        ]
        valid_matches.sort(key=lambda m: m.match_score, reverse=True)
        
        logger.debug(
            f"Matched {len(valid_matches)} agents for capabilities: {capabilities}"
        )
        return valid_matches
    
    def list_all(self, enabled_only: bool = True) -> list[SubAgentConfig]:
        """列出所有 Sub-Agent
        
        Args:
            enabled_only: 是否只列出启用的
        
        Returns:
            Sub-Agent 列表
        """
        agents = list(self._agents.values())
        if enabled_only:
            agents = [a for a in agents if a.enabled]
        
        # 按优先级排序
        agents.sort(key=lambda a: a.priority, reverse=True)
        return agents
    
    def list_capabilities(self) -> list[str]:
        """列出所有能力标签
        
        Returns:
            能力标签列表
        """
        return list(self._capability_index.keys())
    
    def get_stats(self) -> SubAgentRegistryStats:
        """获取注册表统计信息
        
        Returns:
            统计信息
        """
        agents = list(self._agents.values())
        enabled_agents = [a for a in agents if a.enabled]
        
        capability_count: dict[str, int] = {}
        for capability, agent_ids in self._capability_index.items():
            capability_count[capability] = len([
                aid for aid in agent_ids
                if aid in self._agents and self._agents[aid].enabled
            ])
        
        avg_timeout = (
            sum(a.timeout for a in enabled_agents) / len(enabled_agents)
            if enabled_agents else 0
        )
        
        top_priority_agents = [
            a.agent_id for a in sorted(enabled_agents, key=lambda a: a.priority, reverse=True)[:3]
        ]
        
        return SubAgentRegistryStats(
            total_agents=len(agents),
            enabled_agents=len(enabled_agents),
            capability_count=capability_count,
            avg_timeout=avg_timeout,
            top_priority_agents=top_priority_agents,
        )
    
    def update_config(
        self,
        agent_id: str,
        updates: dict,
    ) -> Optional[SubAgentConfig]:
        """更新 Sub-Agent 配置
        
        Args:
            agent_id: Agent ID
            updates: 要更新的字段
        
        Returns:
            更新后的配置，如果不存在返回 None
        """
        config = self.get(agent_id)
        if not config:
            return None
        
        # 应用更新
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # 重新注册以更新索引
        self.register(config)
        
        return config
    
    def enable(self, agent_id: str) -> bool:
        """启用 Sub-Agent"""
        return self.update_config(agent_id, {"enabled": True}) is not None
    
    def disable(self, agent_id: str) -> bool:
        """禁用 Sub-Agent"""
        return self.update_config(agent_id, {"enabled": False}) is not None


_global_registry: Optional[SubAgentRegistry] = None


def get_sub_agent_registry() -> SubAgentRegistry:
    """获取全局 Sub-Agent 注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SubAgentRegistry()
    return _global_registry


def reset_registry() -> None:
    """重置注册表（用于测试）"""
    global _global_registry
    _global_registry = SubAgentRegistry()