"""Soul Manager - Agent Soul 管理器

管理 Agent 的个性特征、价值观和行为准则。
"""

import logging
from datetime import datetime
from typing import Optional

from .memory_models import AgentSoul

logger = logging.getLogger(__name__)

# 默认 Soul 模板
DEFAULT_SOUL = AgentSoul(
    id="default",
    user_id="",
    name="通用助手",
    personality="专业、友好、高效",
    values=["准确性", "用户至上", "持续学习"],
    behavior_rules=[
        "回答问题前先理解用户意图",
        "不确定时主动询问",
        "承认错误并及时纠正",
        "提供可操作的建议",
        "尊重用户的决策",
    ],
    communication_style="清晰简洁，使用专业但易懂的语言",
    expertise_areas=["产品管理", "需求分析", "项目管理"],
)


class SoulManager:
    """Soul 管理器

    管理 Agent Soul 的创建、更新和激活。
    """

    def __init__(self):
        self._souls: dict[str, AgentSoul] = {}

    async def get_active_soul(self, user_id: str) -> AgentSoul:
        """获取用户当前激活的 Soul

        Args:
            user_id: 用户 ID

        Returns:
            激活的 Soul，如果没有则返回默认 Soul
        """
        for soul in self._souls.values():
            if soul.user_id == user_id and soul.is_active:
                return soul

        # 返回默认 Soul
        default = DEFAULT_SOUL.model_copy()
        default.user_id = user_id
        return default

    async def create_soul(self, soul: AgentSoul) -> AgentSoul:
        """创建新 Soul

        Args:
            soul: Soul 对象

        Returns:
            创建的 Soul
        """
        # 如果用户已有激活的 Soul，将其停用
        for existing in self._souls.values():
            if existing.user_id == soul.user_id and existing.is_active:
                existing.is_active = False

        soul.is_active = True
        self._souls[soul.id] = soul
        logger.info(f"Created soul {soul.id} for user {soul.user_id}")
        return soul

    async def update_soul(self, soul_id: str, updates: dict) -> Optional[AgentSoul]:
        """更新 Soul

        Args:
            soul_id: Soul ID
            updates: 要更新的字段

        Returns:
            更新后的 Soul，如果不存在返回 None
        """
        soul = self._souls.get(soul_id)
        if not soul:
            return None

        for key, value in updates.items():
            if hasattr(soul, key) and key not in ("id", "user_id", "created_at"):
                setattr(soul, key, value)

        soul.updated_at = datetime.now()
        return soul

    async def list_souls(self, user_id: str) -> list[AgentSoul]:
        """列出用户的所有 Soul

        Args:
            user_id: 用户 ID

        Returns:
            Soul 列表
        """
        return [s for s in self._souls.values() if s.user_id == user_id]

    async def activate_soul(self, soul_id: str) -> bool:
        """激活指定 Soul

        Args:
            soul_id: Soul ID

        Returns:
            是否激活成功
        """
        soul = self._souls.get(soul_id)
        if not soul:
            return False

        # 停用用户的其他 Soul
        for existing in self._souls.values():
            if existing.user_id == soul.user_id and existing.id != soul_id:
                existing.is_active = False

        soul.is_active = True
        soul.updated_at = datetime.now()
        logger.info(f"Activated soul {soul_id}")
        return True

    async def delete_soul(self, soul_id: str) -> bool:
        """删除 Soul

        Args:
            soul_id: Soul ID

        Returns:
            是否删除成功
        """
        if soul_id not in self._souls:
            return False

        soul = self._souls[soul_id]
        if soul.is_active:
            logger.warning(f"Cannot delete active soul {soul_id}")
            return False

        del self._souls[soul_id]
        logger.info(f"Deleted soul {soul_id}")
        return True

    def build_soul_prompt(self, soul: AgentSoul) -> str:
        """构建 Soul 系统提示词

        Args:
            soul: Soul 对象

        Returns:
            系统提示词
        """
        values_str = "、".join(soul.values)
        rules_str = "\n".join(f"- {rule}" for rule in soul.behavior_rules)
        expertise_str = "、".join(soul.expertise_areas)

        return f"""你是{soul.name}，一个 AI 产品经理助手。

## 个性特征
{soul.personality}

## 核心价值观
{values_str}

## 行为准则
{rules_str}

## 沟通风格
{soul.communication_style}

## 专业领域
{expertise_str}

请始终保持这些特质与用户进行交互。"""

    def build_memory_enhanced_prompt(self, soul: AgentSoul, memories: list[str]) -> str:
        """构建包含记忆的增强提示词

        Args:
            soul: Soul 对象
            memories: 相关记忆列表

        Returns:
            增强的系统提示词
        """
        base_prompt = self.build_soul_prompt(soul)

        if not memories:
            return base_prompt

        memories_str = "\n".join(f"- {m}" for m in memories[:5])

        return f"""{base_prompt}

## 历史记忆
以下是与当前任务相关的历史经验和记忆，请参考：

{memories_str}

请结合这些历史经验来更好地完成当前任务。"""
