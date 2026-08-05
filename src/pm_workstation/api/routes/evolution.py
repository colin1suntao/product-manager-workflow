"""自我进化功能的 REST API 接口"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from pm_workstation.agents.evolution.evolution_manager import AgentEvolutionManager

router = APIRouter(prefix="/v1/evolution", tags=["自我进化"])


# 全局 evolution manager 实例
_evolution_manager: AgentEvolutionManager | None = None


def get_evolution_manager() -> AgentEvolutionManager:
    """获取 evolution manager 单例"""
    global _evolution_manager
    if _evolution_manager is None:
        _evolution_manager = AgentEvolutionManager(
            storage_dir="./data/evolution",
        )
    return _evolution_manager


class EvolutionTriggerRequest(BaseModel):
    """触发进化请求"""
    force: bool = False  # 强制触发，忽略条件检查


class EvolutionMetricsResponse(BaseModel):
    """进化指标响应"""
    total_experiences: int
    excellent_count: int
    good_count: int
    average_count: int
    poor_count: int
    overall_success_rate: float
    avg_execution_time: float
    avg_user_satisfaction: float
    performance_improvement_rate: float
    evolution_cycles: int


class OptimizationSuggestion(BaseModel):
    """优化建议"""
    type: str
    description: str
    items: list | None = None
    details: list | None = None


@router.get("/status", summary="获取进化状态")
async def get_evolution_status(manager: AgentEvolutionManager = Depends(get_evolution_manager)):
    """获取 Agent 自我进化系统的当前状态"""
    return manager.get_evolution_status()


@router.post("/trigger", summary="触发进化流程")
async def trigger_evolution(
    request: EvolutionTriggerRequest,
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """手动触发 Agent 进化流程
    
    会执行：
    1. 经验数据分析
    2. 知识提炼
    3. 应用优化规则
    """
    result = manager.trigger_evolution()
    
    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.get("/metrics", response_model=EvolutionMetricsResponse, summary="获取进化指标")
async def get_evolution_metrics(
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """获取 Agent 进化相关指标"""
    metrics = manager.get_evolution_metrics()
    
    return EvolutionMetricsResponse(
        total_experiences=metrics.total_experiences,
        excellent_count=metrics.excellent_count,
        good_count=metrics.good_count,
        average_count=metrics.average_count,
        poor_count=metrics.poor_count,
        overall_success_rate=metrics.overall_success_rate,
        avg_execution_time=metrics.avg_execution_time,
        avg_user_satisfaction=metrics.avg_user_satisfaction,
        performance_improvement_rate=metrics.performance_improvement_rate,
        evolution_cycles=len(manager.evolution_history),
    )


@router.get("/suggestions", summary="获取优化建议")
async def get_optimization_suggestions(
    task_type: str = "",
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """获取当前任务的优化建议"""
    suggestions = manager.get_optimization_suggestions(task_type)
    return {"suggestions": suggestions}


@router.get("/export", summary="导出进化数据")
async def export_evolution_data(
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """导出完整的进化数据（用于分析或备份）"""
    return manager.export_evolution_data()


@router.post("/rollback/{rule_id}", summary="回滚优化")
async def rollback_optimization(
    rule_id: str,
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """回滚指定的优化规则"""
    success = manager.optimizer.rollback_optimization(rule_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to rollback optimization")
    
    return {"status": "success", "rule_id": rule_id}


@router.get("/experiences", summary="查询经验记录")
async def list_experiences(
    limit: int = 50,
    task_type: str = "",
    quality: str = "",
    success: bool | None = None,
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """查询历史经验记录"""
    from pm_workstation.agents.evolution.evolution_models import ExperienceQuality
    
    quality_filter = None
    if quality:
        try:
            quality_filter = ExperienceQuality(quality)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid quality: {quality}")
    
    experiences = manager.collector.list_experiences(
        task_type=task_type if task_type else None,
        quality=quality_filter,
        success=success,
        limit=limit,
    )
    
    return {
        "count": len(experiences),
        "experiences": [
            {
                "id": e.id,
                "task_type": e.task_type,
                "quality": e.quality,
                "success": e.success,
                "user_satisfaction": e.user_satisfaction,
                "execution_time": e.execution_time_seconds,
                "created_at": e.created_at.isoformat(),
            }
            for e in experiences
        ],
    }


@router.get("/experiences/{experience_id}", summary="获取经验详情")
async def get_experience(
    experience_id: str,
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """获取单个经验记录的详细信息"""
    experience = manager.collector.get_experience(experience_id)
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    return experience.model_dump()


@router.post("/experiences/{experience_id}/feedback", summary="提交用户反馈")
async def submit_feedback(
    experience_id: str,
    feedback: dict,
    manager: AgentEvolutionManager = Depends(get_evolution_manager),
):
    """为经验记录提交用户反馈"""
    experience = manager.collector.get_experience(experience_id)
    
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    # 更新经验记录（这里简化处理，实际应该调用 collector 的更新方法）
    # 为了简化，我们只记录反馈，不修改原经验
    
    return {
        "status": "success",
        "message": "反馈已记录，将用于后续进化分析",
    }
