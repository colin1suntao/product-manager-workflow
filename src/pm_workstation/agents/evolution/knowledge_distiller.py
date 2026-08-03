"""知识提炼器 - 从经验中提取可复用的知识"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pm_workstation.agents.evolution.evolution_models import (
    ExperienceQuality,
    ExperienceRecord,
    OptimizationRule,
)
from pm_workstation.agents.evolution.experience_collector import ExperienceCollector

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    """知识提炼器

    从收集的经验中提炼可复用的知识：
    - 识别成功模式
    - 提取通用规则
    - 生成优化建议
    """

    def __init__(self, collector: ExperienceCollector, storage_dir: str = "./data/evolution/knowledge"):
        self.collector = collector
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.patterns_file = self.storage_dir / "success_patterns.json"
        self.rules_file = self.storage_dir / "optimization_rules.json"

        self._patterns: dict[str, Any] = {}
        self._rules: dict[str, OptimizationRule] = {}
        self._load_knowledge()

    def _load_knowledge(self):
        """加载知识"""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, encoding="utf-8") as f:
                    self._patterns = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load patterns from {self.patterns_file}: {e}")
                self._patterns = {}

        if self.rules_file.exists():
            try:
                with open(self.rules_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self._rules = {}
                    for k, v in data.items():
                        try:
                            self._rules[k] = OptimizationRule(**v)
                        except Exception as e:
                            logger.error(f"Failed to load rule {k}: {e}")
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load rules from {self.rules_file}: {e}")
                self._rules = {}

    def _save_knowledge(self):
        """保存知识"""
        try:
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(self._patterns, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"Failed to save patterns: {e}")

        rules_data = {}
        for k, v in self._rules.items():
            try:
                rules_data[k] = v.model_dump()
            except Exception as e:
                logger.error(f"Failed to serialize rule {k}: {e}")
                rules_data[k] = {"id": k, "error": str(e)}

        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to save rules: {e}")

    def distill(self) -> dict[str, Any]:
        """提炼知识

        Returns:
            提炼结果，包含成功模式、优化规则等
        """
        logger.info("Starting knowledge distillation...")

        # 获取所有经验
        all_experiences = self.collector.list_experiences(limit=1000)

        if len(all_experiences) < 5:
            logger.warning(f"Not enough experiences for distillation: {len(all_experiences)}")
            return {"status": "insufficient_data", "count": len(all_experiences)}

        # 分类经验
        excellent = [e for e in all_experiences if e.quality == ExperienceQuality.EXCELLENT]
        good = [e for e in all_experiences if e.quality == ExperienceQuality.GOOD]
        poor = [e for e in all_experiences if e.quality == ExperienceQuality.POOR]

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_experiences": len(all_experiences),
            "excellent_count": len(excellent),
            "good_count": len(good),
            "poor_count": len(poor),
            "success_patterns": self._extract_success_patterns(excellent),
            "failure_patterns": self._extract_failure_patterns(poor),
            "optimization_rules": self._generate_optimization_rules(all_experiences),
            "best_practices": self._compile_best_practices(excellent + good),
        }

        # 保存提炼结果
        self._patterns['success'] = results['success_patterns']
        self._patterns['failure'] = results['failure_patterns']
        self._patterns['best_practices'] = results['best_practices']
        self._save_knowledge()

        logger.info(f"Knowledge distillation completed: {len(results['optimization_rules'])} rules generated")
        return results

    def _extract_success_patterns(self, experiences: list[ExperienceRecord]) -> list[dict]:
        """提取成功模式"""
        patterns = []

        # 按任务类型分组
        by_type: dict[str, list[ExperienceRecord]] = {}
        for exp in experiences:
            task_type = exp.task_type
            if task_type not in by_type:
                by_type[task_type] = []
            by_type[task_type].append(exp)

        for task_type, exps in by_type.items():
            if len(exps) < 2:
                continue

            # 分析共同特征
            common_skills = self._find_common_elements([e.selected_skills for e in exps])
            common_chain_length = self._average([len(e.agent_chain) for e in exps])
            common_insights = self._find_common_insights(exps)

            pattern = {
                "task_type": task_type,
                "confidence": len(exps) / len(experiences),
                "characteristics": {
                    "common_skills": common_skills,
                    "avg_agent_chain_length": round(common_chain_length, 1),
                    "common_insights": common_insights[:3],
                },
                "metrics": {
                    "avg_execution_time": self._average([e.execution_time_seconds for e in exps]),
                    "avg_satisfaction": self._average([e.user_satisfaction or 3 for e in exps]),
                },
            }
            patterns.append(pattern)

        return patterns

    def _extract_failure_patterns(self, experiences: list[ExperienceRecord]) -> list[dict]:
        """提取失败模式"""
        patterns = []

        # 分析失败原因
        error_types: dict[str, int] = {}
        for exp in experiences:
            if exp.error_message:
                # 简单分类
                if "timeout" in exp.error_message.lower():
                    error_types["timeout"] = error_types.get("timeout", 0) + 1
                elif "token" in exp.error_message.lower():
                    error_types["token_limit"] = error_types.get("token_limit", 0) + 1
                else:
                    error_types["other"] = error_types.get("other", 0) + 1

        for error_type, count in error_types.items():
            patterns.append({
                "error_type": error_type,
                "count": count,
                "percentage": count / len(experiences) if experiences else 0,
            })

        return patterns

    def _generate_optimization_rules(self, experiences: list[ExperienceRecord]) -> list[dict]:
        """生成优化规则"""
        rules = []
        existing_ids = []
        for k in self._rules:
            if k.startswith('opt_'):
                try:
                    existing_ids.append(int(k.split('_')[1]))
                except (ValueError, IndexError):
                    pass
        rule_id = max(existing_ids) if existing_ids else 0

        # 单次遍历分类 + 规则检测
        high_token_exps = []
        slow_exps = []
        many_skills = []

        for e in experiences:
            if sum(e.token_usage.values()) > 50000:
                high_token_exps.append(e)
            if e.execution_time_seconds > 300:
                slow_exps.append(e)
            if len(e.selected_skills) > 5:
                many_skills.append(e)
        if len(high_token_exps) > 3:
            rule_id += 1
            rule = OptimizationRule(
                id=f"opt_{rule_id:03d}",
                name="Token 用量优化",
                description="当 Token 用量过高时，优化 prompt 或切换模型",
                trigger_conditions={"token_threshold": 50000},
                action_type="prompt_adjust",
                action_params={"strategy": "simplify_prompt", "model": "smaller_model"},
                enabled=True,
                confidence=0.8,
            )
            self._rules[rule.id] = rule
            rules.append(rule.model_dump())

        # 规则 2: 执行时间优化
        if len(slow_exps) > 3:
            rule_id += 1
            rule = OptimizationRule(
                id=f"opt_{rule_id:03d}",
                name="执行时间优化",
                description="当执行时间过长时，优化流程或并行执行",
                trigger_conditions={"time_threshold": 300},
                action_type="strategy_switch",
                action_params={"strategy": "parallel_execution"},
                enabled=True,
                confidence=0.75,
            )
            self._rules[rule.id] = rule
            rules.append(rule.model_dump())

        # 规则 3: 技能数量优化
        if len(many_skills) > 3:
            rule_id += 1
            rule = OptimizationRule(
                id=f"opt_{rule_id:03d}",
                name="技能精简",
                description="限制使用的技能数量，聚焦核心技能",
                trigger_conditions={"skill_threshold": 5},
                action_type="parameter_tune",
                action_params={"max_skills": 5},
                enabled=True,
                confidence=0.7,
            )
            self._rules[rule.id] = rule
            rules.append(rule.model_dump())

        self._save_knowledge()
        return rules

    def _compile_best_practices(self, experiences: list[ExperienceRecord]) -> list[dict]:
        """汇编最佳实践"""
        practices = []

        # 收集所有最佳实践
        all_practices: dict[str, int] = {}
        for exp in experiences:
            for practice in exp.best_practices:
                all_practices[practice] = all_practices.get(practice, 0) + 1

        # 按频率排序
        sorted_practices = sorted(all_practices.items(), key=lambda x: x[1], reverse=True)

        for practice, count in sorted_practices[:10]:
            practices.append({
                "practice": practice,
                "frequency": count,
                "confidence": count / len(experiences) if experiences else 0,
            })

        return practices

    def _find_common_elements(self, lists: list[list]) -> list:
        """找出多个列表中的共同元素"""
        if not lists:
            return []

        # 计算每个元素的出现频率
        element_counts: dict[str, int] = {}
        for lst in lists:
            for elem in lst:
                element_counts[elem] = element_counts.get(elem, 0) + 1

        # 返回出现频率 > 50% 的元素
        threshold = len(lists) * 0.5
        return [elem for elem, count in element_counts.items() if count >= threshold]

    def _find_common_insights(self, experiences: list[ExperienceRecord]) -> list[str]:
        """找出共同的洞察"""
        all_insights: dict[str, int] = {}

        for exp in experiences:
            for insight in exp.key_insights:
                # 简化洞察用于归类
                key_insight = insight.split("：")[0] if "：" in insight else insight[:30]
                all_insights[key_insight] = all_insights.get(key_insight, 0) + 1

        sorted_insights = sorted(all_insights.items(), key=lambda x: x[1], reverse=True)
        return [insight for insight, _ in sorted_insights[:5]]

    def _average(self, values: list[float]) -> float:
        """计算平均值"""
        if not values:
            return 0.0
        return sum(values) / len(values)

    def get_optimization_rules(self) -> list[OptimizationRule]:
        """获取优化规则"""
        return list(self._rules.values())

    def get_best_practices(self, task_type: str | None = None) -> list[dict]:
        """获取最佳实践"""
        practices = self._patterns.get('best_practices', [])

        if task_type:
            # 过滤特定任务类型的实践
            filtered = [p for p in practices if task_type in p.get('practice', '')]
            return filtered if filtered else practices

        return practices
