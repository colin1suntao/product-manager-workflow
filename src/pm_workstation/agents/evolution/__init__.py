"""自我进化功能模块

使 Agent 能够从历史任务中学习、分析成功/失败模式、
自动优化策略、积累最佳实践，持续提升任务执行质量。
"""

from pm_workstation.agents.evolution.evolution_manager import AgentEvolutionManager
from pm_workstation.agents.evolution.evolution_models import (
    AgentEvolutionConfig,
    EvolutionMetrics,
    EvolutionStatus,
    ExperienceQuality,
    ExperienceRecord,
    ExperienceType,
    OptimizationRule,
)
from pm_workstation.agents.evolution.experience_collector import ExperienceCollector
from pm_workstation.agents.evolution.knowledge_distiller import KnowledgeDistiller
from pm_workstation.agents.evolution.strategy_optimizer import StrategyOptimizer

__all__ = [
    # Manager
    "AgentEvolutionManager",

    # Models
    "AgentEvolutionConfig",
    "EvolutionMetrics",
    "EvolutionStatus",
    "ExperienceQuality",
    "ExperienceRecord",
    "ExperienceType",
    "OptimizationRule",

    # Collectors
    "ExperienceCollector",
    "KnowledgeDistiller",
    "StrategyOptimizer",
]
