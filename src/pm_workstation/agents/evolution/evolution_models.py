"""自我进化功能的数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EvolutionStatus(str, Enum):
    """进化状态"""
    COLLECTING = "collecting"  # 收集中
    ANALYZING = "analyzing"  # 分析中
    OPTIMIZING = "optimizing"  # 优化中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class ExperienceQuality(str, Enum):
    """经验质量评级"""
    EXCELLENT = "excellent"  # 优秀 - 可复用
    GOOD = "good"  # 良好 - 有参考价值
    AVERAGE = "average"  # 一般 - 普通案例
    POOR = "poor"  # 较差 - 失败案例


class ExperienceType(str, Enum):
    """经验类型"""
    TASK_SUCCESS = "task_success"  # 任务成功
    TASK_FAILURE = "task_failure"  # 任务失败
    USER_FEEDBACK = "user_feedback"  # 用户反馈
    PERFORMANCE_METRIC = "performance_metric"  # 性能指标
    BEST_PRACTICE = "best_practice"  # 最佳实践
    PROMPT_OPTIMIZATION = "prompt_optimization"  # Prompt 优化
    STRATEGY_ADJUSTMENT = "strategy_adjustment"  # 策略调整


class ExperienceRecord(BaseModel):
    """经验记录"""
    id: str = Field(..., description="经验 ID")
    workflow_id: str = Field(..., description="关联的工作流 ID")
    task_type: str = Field(..., description="任务类型")
    experience_type: ExperienceType = Field(..., description="经验类型")
    quality: ExperienceQuality = Field(default=ExperienceQuality.AVERAGE, description="质量评级")
    
    # 任务上下文
    requirement_text: str = Field(..., description="需求描述")
    selected_skills: list[str] = Field(default_factory=list, description="使用的技能")
    agent_chain: list[str] = Field(default_factory=list, description="Agent 执行链")
    
    # 执行结果
    success: bool = Field(..., description="是否成功")
    error_message: str | None = Field(None, description="错误消息")
    user_feedback: str | None = Field(None, description="用户反馈")
    user_satisfaction: int | None = Field(None, ge=1, le=5, description="用户满意度 (1-5)")
    
    # 性能指标
    execution_time_seconds: float = Field(default=0.0, description="执行时间 (秒)")
    token_usage: dict[str, int] = Field(default_factory=dict, description="Token 用量")
    retry_count: int = Field(default=0, description="重试次数")
    
    # 提取的知识
    key_insights: list[str] = Field(default_factory=list, description="关键洞察")
    best_practices: list[str] = Field(default_factory=list, description="最佳实践")
    pitfalls: list[str] = Field(default_factory=list, description="陷阱/注意事项")
    optimization_suggestions: list[str] = Field(default_factory=list, description="优化建议")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    version: str = Field(default="1.0", description="Agent 版本")
    
    class Config:
        use_enum_values = True


class EvolutionMetrics(BaseModel):
    """进化指标"""
    total_experiences: int = Field(default=0, description="总经验数")
    excellent_count: int = Field(default=0, description="优秀经验数")
    good_count: int = Field(default=0, description="良好经验数")
    average_count: int = Field(default=0, description="一般经验数")
    poor_count: int = Field(default=0, description="较差经验数")
    
    # 成功率统计
    overall_success_rate: float = Field(default=0.0, ge=0, le=1, description="总体成功率")
    success_rate_by_type: dict[str, float] = Field(default_factory=dict, description="按任务类型的成功率")
    
    # 性能趋势
    avg_execution_time: float = Field(default=0.0, description="平均执行时间")
    avg_token_usage: int = Field(default=0, description="平均 Token 用量")
    avg_user_satisfaction: float = Field(default=0.0, ge=0, le=5, description="平均用户满意度")
    
    # 改进追踪
    improvements_applied: int = Field(default=0, description="已应用的改进数")
    performance_improvement_rate: float = Field(default=0.0, description="性能提升率")
    
    # 时间周期
    period_start: datetime = Field(..., description="统计周期开始")
    period_end: datetime = Field(..., description="统计周期结束")


class OptimizationRule(BaseModel):
    """优化规则"""
    id: str = Field(..., description="规则 ID")
    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    
    # 触发条件
    trigger_conditions: dict[str, Any] = Field(default_factory=dict, description="触发条件")
    
    # 优化动作
    action_type: str = Field(..., description="动作类型")  # prompt_adjust, parameter_tune, strategy_switch
    action_params: dict[str, Any] = Field(default_factory=dict, description="动作参数")
    
    # 效果验证
    expected_improvement: float = Field(default=0.0, description="预期提升")
    actual_improvement: float | None = Field(None, description="实际提升")
    
    # 状态
    enabled: bool = Field(default=True, description="是否启用")
    confidence: float = Field(default=0.0, ge=0, le=1, description="置信度")
    apply_count: int = Field(default=0, description="应用次数")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


class AgentEvolutionConfig(BaseModel):
    """Agent 进化配置"""
    enabled: bool = Field(default=True, description="是否启用自我进化")
    auto_apply_optimizations: bool = Field(default=False, description="是否自动应用优化")
    min_confidence_threshold: float = Field(default=0.7, ge=0, le=1, description="最小置信度阈值")
    
    # 经验收集
    collect_experiences: bool = Field(default=True, description="收集经验")
    min_quality_for_learning: ExperienceQuality = Field(default=ExperienceQuality.GOOD, description="学习最低质量")
    
    # 分析频率
    analysis_interval_hours: int = Field(default=24, description="分析间隔 (小时)")
    min_experiences_for_analysis: int = Field(default=10, description="分析所需最少经验数")
    
    # 优化策略
    max_optimizations_per_cycle: int = Field(default=5, description="每周期最大优化数")
    optimization_methods: list[str] = Field(default_factory=list, description="优化方法列表")
    
    # 回滚策略
    enable_rollback: bool = Field(default=True, description="启用回滚")
    rollback_on_failure: bool = Field(default=True, description="失败时回滚")
