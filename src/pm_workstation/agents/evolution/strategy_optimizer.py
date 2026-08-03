"""策略优化器 - 应用优化规则改进 Agent 表现"""

import logging
from copy import deepcopy
from typing import Any

from pm_workstation.agents.evolution.evolution_models import (
    EvolutionMetrics,
    OptimizationRule,
)
from pm_workstation.agents.evolution.knowledge_distiller import KnowledgeDistiller

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """策略优化器

    根据提炼的知识优化 Agent 策略：
    - Prompt 优化
    - 参数调优
    - 策略切换
    """

    def __init__(self, distiller: KnowledgeDistiller):
        self.distiller = distiller
        self.optimization_history: list[dict] = []
        self.current_strategies: dict[str, Any] = self._load_default_strategies()

    def _load_default_strategies(self) -> dict[str, Any]:
        """加载默认策略"""
        return {
            "prompt_templates": {},
            "model_parameters": {
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "execution_config": {
                "parallel_enabled": False,
                "max_parallel_tasks": 3,
                "timeout_seconds": 300,
            },
            "skill_config": {
                "max_skills": 5,
                "recommended_only": False,
            },
        }

    def apply_optimizations(self) -> list[dict]:
        """应用优化

        Returns:
            应用的优化列表
        """
        rules = self.distiller.get_optimization_rules()
        applied = []

        for rule in rules:
            if not rule.enabled:
                continue

            logger.info(f"Applying optimization rule: {rule.name}")

            try:
                if rule.action_type == "prompt_adjust":
                    result = self._adjust_prompt(rule)
                elif rule.action_type == "parameter_tune":
                    result = self._tune_parameters(rule)
                elif rule.action_type == "strategy_switch":
                    result = self._switch_strategy(rule)
                else:
                    logger.warning(f"Unknown action type: {rule.action_type}")
                    continue

                if result:
                    applied.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "action_type": rule.action_type,
                        "result": result,
                    })

                    # 更新规则统计
                    rule.apply_count += 1
            except Exception as e:
                logger.error(f"Failed to apply rule {rule.id}: {e}")

        self.optimization_history.append({
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "applied_count": len(applied),
            "optimizations": applied,
        })

        return applied

    def _adjust_prompt(self, rule: OptimizationRule) -> dict | None:
        """调整 Prompt"""
        strategy = rule.action_params.get("strategy", "")

        if strategy == "simplify_prompt":
            # 简化 prompt 的策略
            logger.info("Applying prompt simplification strategy")

            # 这里可以实际修改 prompt 模板
            # 为了演示，我们只记录策略变化
            self.current_strategies['prompt_templates']['simplified'] = True

            return {
                "changes": {
                    "simplified": True,
                    "max_tokens_reduced": True,
                }
            }

        return None

    def _tune_parameters(self, rule: OptimizationRule) -> dict | None:
        """调整参数"""
        changes = {}

        if "max_skills" in rule.action_params:
            old_value = self.current_strategies['skill_config']['max_skills']
            new_value = rule.action_params['max_skills']
            self.current_strategies['skill_config']['max_skills'] = new_value
            changes['max_skills'] = {"from": old_value, "to": new_value}

        if "temperature" in rule.action_params:
            old_value = self.current_strategies['model_parameters']['temperature']
            new_value = rule.action_params['temperature']
            self.current_strategies['model_parameters']['temperature'] = new_value
            changes['temperature'] = {"from": old_value, "to": new_value}

        if changes:
            return {"parameters_changed": changes}

        return None

    def _switch_strategy(self, rule: OptimizationRule) -> dict | None:
        """切换策略"""
        strategy = rule.action_params.get("strategy", "")

        if strategy == "parallel_execution":
            logger.info("Enabling parallel execution strategy")
            old_value = self.current_strategies['execution_config']['parallel_enabled']
            self.current_strategies['execution_config']['parallel_enabled'] = True
            return {
                "strategy_change": {
                    "parallel_enabled": {"from": old_value, "to": True},
                }
            }

        return None

    def get_optimization_suggestions(self, task_context: dict) -> list[dict]:
        """根据任务上下文获取优化建议

        Args:
            task_context: 任务上下文，包含 task_type, complexity, etc.

        Returns:
            优化建议列表
        """
        suggestions = []

        # 基于历史优化的建议
        if self.optimization_history:
            last_optimization = self.optimization_history[-1]
            suggestions.append({
                "type": "recent_optimization",
                "description": f"最近应用了 {last_optimization['applied_count']} 个优化",
                "details": last_optimization['optimizations'],
            })

        # 基于最佳实践的建议
        practices = self.distiller.get_best_practices(task_context.get('task_type'))
        if practices:
            suggestions.append({
                "type": "best_practices",
                "description": "推荐的最佳实践",
                "practices": practices[:3],
            })

        return suggestions

    def rollback_optimization(self, rule_id: str) -> bool:
        """回滚优化

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功回滚
        """
        rules = self.distiller.get_optimization_rules()
        rule = next((r for r in rules if r.id == rule_id), None)

        if not rule:
            logger.warning(f"Rule not found: {rule_id}")
            return False

        # 根据规则类型回滚
        if rule.action_type == "prompt_adjust":
            self.current_strategies['prompt_templates'].pop('simplified', None)
        elif rule.action_type == "parameter_tune":
            # 恢复默认参数
            defaults = self._load_default_strategies()
            for key in rule.action_params:
                if key in defaults['skill_config']:
                    self.current_strategies['skill_config'][key] = defaults['skill_config'][key]
                elif key in defaults['model_parameters']:
                    self.current_strategies['model_parameters'][key] = defaults['model_parameters'][key]
        elif rule.action_type == "strategy_switch":
            # 恢复默认策略
            defaults = self._load_default_strategies()
            self.current_strategies['execution_config'] = deepcopy(defaults['execution_config'])

        # 禁用规则
        rule.enabled = False

        logger.info(f"Rolled back optimization: {rule_id}")
        return True

    def get_current_strategies(self) -> dict[str, Any]:
        """获取当前策略"""
        return deepcopy(self.current_strategies)

    def calculate_improvement(self, before_metrics: EvolutionMetrics, after_metrics: EvolutionMetrics) -> float:
        """计算改进幅度

        Args:
            before_metrics: 优化前指标
            after_metrics: 优化后指标

        Returns:
            改进百分比
        """
        improvements = []

        # 成功率改进
        if before_metrics.overall_success_rate > 0:
            rate_improvement = (
                (after_metrics.overall_success_rate - before_metrics.overall_success_rate)
                / before_metrics.overall_success_rate
            )
            improvements.append(rate_improvement)

        # 执行时间改进
        if before_metrics.avg_execution_time > 0:
            time_improvement = (
                (before_metrics.avg_execution_time - after_metrics.avg_execution_time)
                / before_metrics.avg_execution_time
            )
            improvements.append(time_improvement)

        # 用户满意度改进
        if before_metrics.avg_user_satisfaction > 0:
            satisfaction_improvement = (
                (after_metrics.avg_user_satisfaction - before_metrics.avg_user_satisfaction)
                / 5.0  # 归一化到 0-1
            )
            improvements.append(satisfaction_improvement)

        # 平均改进幅度
        if improvements:
            return sum(improvements) / len(improvements) * 100  # 百分比

        return 0.0
