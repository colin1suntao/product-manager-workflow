"""自我进化系统的进化管理器"""

import logging
from datetime import datetime, timedelta
from typing import Any

from pm_workstation.agents.evolution.evolution_models import (
    AgentEvolutionConfig,
    EvolutionMetrics,
    EvolutionStatus,
    ExperienceQuality,
)
from pm_workstation.agents.evolution.experience_collector import ExperienceCollector
from pm_workstation.agents.evolution.knowledge_distiller import KnowledgeDistiller
from pm_workstation.agents.evolution.strategy_optimizer import StrategyOptimizer
from pm_workstation.orchestrator.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class AgentEvolutionManager:
    """Agent 进化管理器
    
    统筹整个自我进化流程：
    1. 收集经验
    2. 定期分析
    3. 应用优化
    4. 追踪效果
    """
    
    def __init__(
        self,
        storage_dir: str = "./data/evolution",
        config: AgentEvolutionConfig | None = None,
    ):
        self.storage_dir = storage_dir
        self.config = config or AgentEvolutionConfig()
        
        # 初始化子组件
        self.collector = ExperienceCollector(
            storage_dir=f"{storage_dir}/experiences"
        )
        self.distiller = KnowledgeDistiller(
            collector=self.collector,
            storage_dir=f"{storage_dir}/knowledge",
        )
        self.optimizer = StrategyOptimizer(self.distiller)
        
        # 状态追踪
        self.status = EvolutionStatus.COLLECTING
        self.last_analysis_time: datetime | None = None
        self.evolution_history: list[dict] = []
        
        # 指标快照（用于计算改进）
        self.baseline_metrics: EvolutionMetrics | None = None
    
    def collect_experience(
        self,
        state: WorkflowState,
        user_feedback: str | None = None,
    ) -> dict:
        """收集经验
        
        Args:
            state: 工作流状态
            user_feedback: 用户反馈
            
        Returns:
            收集结果
        """
        if not self.config.collect_experiences:
            return {"status": "disabled"}
        
        try:
            experience = self.collector.collect_from_workflow(state, user_feedback)
            
            # 检查是否需要分析
            should_analyze = self._should_trigger_analysis()
            
            return {
                "status": "collected",
                "experience_id": experience.id,
                "quality": experience.quality,
                "should_analyze": should_analyze,
            }
        except Exception as e:
            logger.error(f"Failed to collect experience: {e}")
            return {"status": "error", "error": str(e)}
    
    def trigger_evolution(self) -> dict[str, Any]:
        """触发进化流程
        
        Returns:
            进化结果
        """
        logger.info("Starting agent evolution cycle...")
        self.status = EvolutionStatus.ANALYZING
        
        try:
            # 1. 知识提炼
            distillation_result = self.distiller.distill()
            
            if distillation_result.get("status") == "insufficient_data":
                self.status = EvolutionStatus.COLLECTING
                return {
                    "status": "skipped",
                    "reason": "insufficient_data",
                    "details": distillation_result,
                }
            
            # 2. 应用优化
            self.status = EvolutionStatus.OPTIMIZING
            optimizations = self.optimizer.apply_optimizations()
            
            # 3. 记录进化历史
            evolution_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "distillation": distillation_result,
                "optimizations_applied": len(optimizations),
                "optimizations": optimizations,
            }
            self.evolution_history.append(evolution_record)
            
            # 4. 更新状态
            self.last_analysis_time = datetime.utcnow()
            self.status = EvolutionStatus.COMPLETED
            
            # 5. 如果配置了自动应用，标记需要重启
            auto_restart = self.config.auto_apply_optimizations
            
            logger.info(f"Evolution cycle completed: {len(optimizations)} optimizations applied")
            
            return {
                "status": "completed",
                "distillation_summary": {
                    "total_experiences": distillation_result.get("total_experiences"),
                    "success_patterns": len(distillation_result.get("success_patterns", [])),
                    "optimization_rules": len(optimizations),
                },
                "optimizations": optimizations,
                "auto_restart": auto_restart,
            }
            
        except Exception as e:
            logger.error(f"Evolution cycle failed: {e}")
            self.status = EvolutionStatus.FAILED
            return {
                "status": "failed",
                "error": str(e),
            }
    
    def _should_trigger_analysis(self) -> bool:
        """检查是否应该触发分析"""
        # 检查经验数量
        all_experiences = self.collector.list_experiences(limit=self.config.min_experiences_for_analysis + 1)
        if len(all_experiences) < self.config.min_experiences_for_analysis:
            return False
        
        # 检查时间间隔
        if self.last_analysis_time:
            hours_since_last = (datetime.utcnow() - self.last_analysis_time).total_seconds() / 3600
            if hours_since_last < self.config.analysis_interval_hours:
                return False
        
        return True
    
    def get_evolution_metrics(self) -> EvolutionMetrics:
        """获取进化指标"""
        all_experiences = self.collector.list_experiences(limit=1000)

        if not all_experiences:
            return EvolutionMetrics(
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow(),
            )

        # 单次遍历聚合所有指标（替代原来 7+ 次遍历）
        quality_count = {"excellent": 0, "good": 0, "average": 0, "poor": 0}
        success_count = 0
        total_time = 0
        total_tokens = 0
        total_satisfaction = 0
        satisfaction_count = 0
        by_type: dict[str, list[ExperienceRecord]] = {}

        for e in all_experiences:
            quality_count[e.quality] += 1
            if e.success:
                success_count += 1
            total_time += e.execution_time_seconds
            total_tokens += sum(e.token_usage.values())
            if e.user_satisfaction is not None:
                total_satisfaction += e.user_satisfaction
                satisfaction_count += 1
            if e.task_type not in by_type:
                by_type[e.task_type] = []
            by_type[e.task_type].append(e)

        n = len(all_experiences)
        success_rate_by_type = {}
        for task_type, exps in by_type.items():
            successes = sum(1 for e in exps if e.success)
            success_rate_by_type[task_type] = successes / len(exps)

        avg_time = total_time / n
        avg_tokens = total_tokens / n
        avg_satisfaction = total_satisfaction / satisfaction_count if satisfaction_count else 0.0

        excellent_count = quality_count["excellent"]
        good_count = quality_count["good"]
        average_count = quality_count["average"]
        poor_count = quality_count["poor"]
        
        # 计算改进率
        improvement_rate = 0.0
        if self.baseline_metrics:
            current_metrics = EvolutionMetrics(
                total_experiences=n,
                excellent_count=excellent_count,
                good_count=good_count,
                average_count=average_count,
                poor_count=poor_count,
                overall_success_rate=success_count / n,
                success_rate_by_type=success_rate_by_type,
                avg_execution_time=avg_time,
                avg_token_usage=int(avg_tokens),
                avg_user_satisfaction=avg_satisfaction,
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
            )
            improvement_rate = self.optimizer.calculate_improvement(
                self.baseline_metrics, current_metrics
            )
            self.baseline_metrics = current_metrics
        else:
            self.baseline_metrics = EvolutionMetrics(
                total_experiences=n,
                excellent_count=excellent_count,
                good_count=good_count,
                average_count=average_count,
                poor_count=poor_count,
                overall_success_rate=success_count / n,
                success_rate_by_type=success_rate_by_type,
                avg_execution_time=avg_time,
                avg_token_usage=int(avg_tokens),
                avg_user_satisfaction=avg_satisfaction,
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
            )
        
        return EvolutionMetrics(
            total_experiences=n,
            excellent_count=excellent_count,
            good_count=good_count,
            average_count=average_count,
            poor_count=poor_count,
            overall_success_rate=success_count / n,
            success_rate_by_type=success_rate_by_type,
            avg_execution_time=avg_time,
            avg_token_usage=int(avg_tokens),
            avg_user_satisfaction=avg_satisfaction,
            improvements_applied=len(self.evolution_history),
            performance_improvement_rate=improvement_rate,
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
        )
    
    def get_optimization_suggestions(self, task_type: str = "") -> list[dict]:
        """获取优化建议
        
        Args:
            task_type: 任务类型
            
        Returns:
            优化建议列表
        """
        suggestions = self.optimizer.get_optimization_suggestions({"task_type": task_type})
        
        # 添加最佳实践建议
        practices = self.distiller.get_best_practices(task_type if task_type else None)
        if practices:
            suggestions.append({
                "type": "best_practices",
                "description": "从历史数据中学到的最佳实践",
                "items": practices[:5],
            })
        
        return suggestions
    
    def get_evolution_status(self) -> dict[str, Any]:
        """获取进化状态"""
        metrics = self.get_evolution_metrics()
        
        return {
            "status": self.status.value,
            "enabled": self.config.enabled,
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "metrics": metrics.model_dump(),
            "evolution_cycles": len(self.evolution_history),
            "current_strategies": self.optimizer.get_current_strategies(),
        }
    
    def export_evolution_data(self) -> dict[str, Any]:
        """导出进化数据
        
        Returns:
            完整的进化数据
        """
        return {
            "config": self.config.model_dump(),
            "metrics": self.get_evolution_metrics().model_dump(),
            "evolution_history": self.evolution_history,
            "optimization_rules": [r.model_dump() for r in self.distiller.get_optimization_rules()],
            "best_practices": self.distiller.get_best_practices(),
            "current_strategies": self.optimizer.get_current_strategies(),
        }
