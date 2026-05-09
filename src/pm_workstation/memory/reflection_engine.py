"""Reflection Engine - 反思引擎

负责定期反思历史工作，总结经验教训，生成学习记录。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from .memory_manager import MemoryManager
from .memory_models import MemoryEntry, MemoryType, Reflection

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """反思引擎

    分析历史任务，识别模式，生成反思报告和学习记录。
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self._reflections: dict[str, Reflection] = {}

    async def check_reflection_trigger(self, user_id: str) -> bool:
        """检查是否需要触发反思

        Args:
            user_id: 用户 ID

        Returns:
            是否需要反思
        """
        # 获取最新反思
        latest = await self.get_latest_reflection(user_id)

        if not latest:
            # 从未反思过，检查是否有足够的记忆
            memories = await self.memory_manager.list_memories(user_id, limit=10)
            return len(memories) >= 5

        # 检查距离上次反思是否超过 24 小时
        time_since_last = datetime.now() - latest.created_at
        if time_since_last < timedelta(hours=24):
            return False

        # 检查是否有新记忆
        new_memories = await self.memory_manager.list_memories(user_id, limit=10)
        return len(new_memories) >= 3

    async def execute_reflection(self, user_id: str) -> Reflection:
        """执行反思

        Args:
            user_id: 用户 ID

        Returns:
            反思记录
        """
        logger.info(f"Executing reflection for user {user_id}")

        # 获取最近的记忆
        recent_memories = await self.memory_manager.list_memories(
            user_id=user_id,
            limit=50,
        )

        # 分析模式
        analysis = await self.analyze_patterns(recent_memories)

        # 生成学习点
        learnings = await self.generate_learnings(analysis)

        # 确定改进领域
        improvement_areas = self._identify_improvement_areas(analysis)

        # 生成行动项
        action_items = self._generate_action_items(learnings, improvement_areas)

        # 计算时间范围
        if recent_memories:
            period_end = datetime.now()
            period_start = min(m.created_at for m in recent_memories)
        else:
            period_end = datetime.now()
            period_start = period_end - timedelta(days=7)

        # 创建反思记录
        reflection = Reflection(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            total_tasks=analysis.get("total_tasks", 0),
            successful_tasks=analysis.get("successful_tasks", 0),
            failed_tasks=analysis.get("failed_tasks", 0),
            key_learnings=learnings,
            improvement_areas=improvement_areas,
            action_items=action_items,
        )

        self._reflections[reflection.id] = reflection

        # 将学习点保存为记忆
        for learning in learnings:
            memory = MemoryEntry(
                user_id=user_id,
                memory_type=MemoryType.LEARNING,
                content=learning,
                summary=f"反思学习: {learning[:50]}...",
                tags=["reflection", "learning"],
                importance=0.7,
                source=reflection.id,
            )
            await self.memory_manager.add_memory(memory)

        logger.info(f"Reflection completed: {len(learnings)} learnings generated")
        return reflection

    async def analyze_patterns(self, memories: list[MemoryEntry]) -> dict:
        """分析记忆中的模式

        Args:
            memories: 记忆列表

        Returns:
            分析结果
        """
        analysis = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "common_errors": {},
            "success_patterns": {},
            "task_types": {},
        }

        for memory in memories:
            if memory.memory_type in (MemoryType.EXPERIENCE, MemoryType.MISTAKE):
                analysis["total_tasks"] += 1

                if memory.memory_type == MemoryType.EXPERIENCE:
                    analysis["successful_tasks"] += 1
                    # 分析成功模式
                    for tag in memory.tags:
                        if tag not in ("success",):
                            analysis["success_patterns"][tag] = \
                                analysis["success_patterns"].get(tag, 0) + 1
                else:
                    analysis["failed_tasks"] += 1
                    # 分析错误模式
                    for tag in memory.tags:
                        if tag not in ("failure", "error"):
                            analysis["common_errors"][tag] = \
                                analysis["common_errors"].get(tag, 0) + 1

                # 统计任务类型
                task_type = memory.context.get("task_type", "unknown")
                analysis["task_types"][task_type] = \
                    analysis["task_types"].get(task_type, 0) + 1

        return analysis

    async def generate_learnings(self, analysis: dict) -> list[str]:
        """生成学习点

        Args:
            analysis: 分析结果

        Returns:
            学习点列表
        """
        learnings = []

        # 从错误中学习
        if analysis["common_errors"]:
            top_errors = sorted(
                analysis["common_errors"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            for error, count in top_errors:
                learnings.append(f"常见错误: {error} (出现 {count} 次)，需要特别注意避免")

        # 从成功中学习
        if analysis["success_patterns"]:
            top_successes = sorted(
                analysis["success_patterns"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            for pattern, count in top_successes:
                learnings.append(f"成功模式: {pattern} (成功 {count} 次)，应继续使用")

        # 任务类型分析
        if analysis["task_types"]:
            most_common = max(analysis["task_types"].items(), key=lambda x: x[1])
            learnings.append(f"最常处理的任务类型: {most_common[0]} ({most_common[1]} 次)")

        # 成功率分析
        total = analysis["total_tasks"]
        if total > 0:
            success_rate = analysis["successful_tasks"] / total
            if success_rate < 0.7:
                learnings.append(f"成功率较低 ({success_rate:.0%})，需要加强错误预防")
            elif success_rate > 0.9:
                learnings.append(f"成功率很高 ({success_rate:.0%})，保持良好状态")

        return learnings

    def _identify_improvement_areas(self, analysis: dict) -> list[str]:
        """识别改进领域

        Args:
            analysis: 分析结果

        Returns:
            改进领域列表
        """
        areas = []

        # 基于错误频率识别改进领域
        if analysis["common_errors"]:
            top_errors = sorted(
                analysis["common_errors"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            for error, count in top_errors:
                if count >= 2:
                    areas.append(f"改进 {error} 相关的处理流程")

        # 基于成功率识别改进领域
        total = analysis["total_tasks"]
        if total > 0:
            success_rate = analysis["successful_tasks"] / total
            if success_rate < 0.8:
                areas.append("加强任务执行前的需求确认")
                areas.append("完善错误处理和降级策略")

        return areas

    def _generate_action_items(
        self,
        learnings: list[str],
        improvement_areas: list[str],
    ) -> list[str]:
        """生成行动项

        Args:
            learnings: 学习点
            improvement_areas: 改进领域

        Returns:
            行动项列表
        """
        actions = []

        # 基于学习点生成行动项
        for learning in learnings[:3]:
            if "错误" in learning:
                actions.append(f"针对 {learning[:30]}... 制定预防措施")
            elif "成功" in learning:
                actions.append(f"继续应用 {learning[:30]}... 的成功经验")

        # 基于改进领域生成行动项
        for area in improvement_areas[:2]:
            actions.append(f"制定 {area} 的具体改进计划")

        # 通用行动项
        if not actions:
            actions.append("继续积累经验，定期回顾和反思")

        return actions

    async def get_latest_reflection(self, user_id: str) -> Optional[Reflection]:
        """获取用户的最新反思记录

        Args:
            user_id: 用户 ID

        Returns:
            最新的反思记录，如果没有返回 None
        """
        user_reflections = [
            r for r in self._reflections.values()
            if r.user_id == user_id
        ]

        if not user_reflections:
            return None

        return max(user_reflections, key=lambda r: r.created_at)

    async def list_reflections(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[Reflection]:
        """列出用户的反思记录

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            反思记录列表
        """
        user_reflections = [
            r for r in self._reflections.values()
            if r.user_id == user_id
        ]

        # 按创建时间倒序排列
        user_reflections.sort(key=lambda r: r.created_at, reverse=True)

        return user_reflections[:limit]
