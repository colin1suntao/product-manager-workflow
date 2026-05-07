"""推理路径记录器"""

from datetime import datetime

from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    """推理步骤"""
    step_number: int  # 步骤序号
    action: str  # 动作（parse/analyze/decompose/detect等）
    description: str  # 步骤描述
    input_data: str | None = None  # 输入数据摘要
    output_data: str | None = None  # 输出数据摘要
    duration_ms: int | None = None  # 耗时（毫秒）
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReasoningTrace(BaseModel):
    """推理路径"""
    trace_id: str  # 追踪ID
    requirement_text: str  # 原始需求
    steps: list[ReasoningStep] = Field(default_factory=list)  # 推理步骤
    started_at: datetime = Field(default_factory=datetime.utcnow)  # 开始时间
    completed_at: datetime | None = None  # 完成时间
    total_duration_ms: int | None = None  # 总耗时
    status: str = "in_progress"  # 状态 (in_progress/completed/failed)
    error_message: str | None = None  # 错误信息

    def add_step(
        self,
        action: str,
        description: str,
        input_data: str | None = None,
        output_data: str | None = None,
        duration_ms: int | None = None,
    ) -> ReasoningStep:
        """添加推理步骤

        Args:
            action: 动作
            description: 描述
            input_data: 输入数据摘要
            output_data: 输出数据摘要
            duration_ms: 耗时

        Returns:
            推理步骤
        """
        step = ReasoningStep(
            step_number=len(self.steps) + 1,
            action=action,
            description=description,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step

    def complete(self, error_message: str | None = None):
        """完成推理

        Args:
            error_message: 错误信息（如果有）
        """
        self.completed_at = datetime.utcnow()

        if self.steps:
            total_ms = sum(step.duration_ms or 0 for step in self.steps)
            self.total_duration_ms = total_ms

        if error_message:
            self.status = "failed"
            self.error_message = error_message
        else:
            self.status = "completed"

    def get_summary(self) -> str:
        """获取推理摘要"""
        lines = [
            f"推理路径 #{self.trace_id}",
            f"状态: {self.status}",
            f"步骤数: {len(self.steps)}",
        ]

        if self.total_duration_ms:
            lines.append(f"总耗时: {self.total_duration_ms}ms")

        lines.append("")
        lines.append("推理步骤:")

        for step in self.steps:
            duration = f" ({step.duration_ms}ms)" if step.duration_ms else ""
            lines.append(f"  {step.step_number}. [{step.action}] {step.description}{duration}")

        if self.error_message:
            lines.append(f"\n错误: {self.error_message}")

        return "\n".join(lines)


class ReasoningTracer:
    """推理路径记录器"""

    def __init__(self):
        self.traces: dict[str, ReasoningTrace] = {}

    def start_trace(self, trace_id: str, requirement_text: str) -> ReasoningTrace:
        """开始推理追踪

        Args:
            trace_id: 追踪ID
            requirement_text: 原始需求

        Returns:
            推理路径
        """
        trace = ReasoningTrace(
            trace_id=trace_id,
            requirement_text=requirement_text,
        )
        self.traces[trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> ReasoningTrace | None:
        """获取推理路径

        Args:
            trace_id: 追踪ID

        Returns:
            推理路径
        """
        return self.traces.get(trace_id)

    def get_all_traces(self) -> list[ReasoningTrace]:
        """获取所有推理路径

        Returns:
            推理路径列表
        """
        return list(self.traces.values())

    def clear_traces(self):
        """清除所有推理路径"""
        self.traces.clear()
