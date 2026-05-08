"""工作流状态定义

定义 LangGraph 工作流中使用的状态结构。
"""


from pydantic import BaseModel, Field

from pm_workstation.models.core import (
    StructuredRequirement,
    VerificationReport,
    WorkflowRun,
    WorkflowStatus,
)
from pm_workstation.prototype.page_structure import PageStructure


class WorkflowState(BaseModel):
    """LangGraph 工作流状态

    在工作流执行过程中传递和共享的数据。
    """
    workflow_run: WorkflowRun = Field(..., description="工作流运行记录")

    # 解析阶段产物
    structured_requirement: StructuredRequirement | None = Field(
        default=None,
        description="结构化需求",
    )
    reasoning_trace: str = Field(default="", description="推理路径记录")
    clarification_questions: list[dict] = Field(default_factory=list, description="待澄清问题列表")

    # 生成阶段产物
    page_structure: PageStructure | None = Field(default=None, description="页面结构")
    prototype_html: str = Field(default="", description="原型 HTML 内容")
    prd_document: str = Field(default="", description="PRD 文档内容")

    # 校验阶段产物
    verification_report: VerificationReport | None = Field(default=None, description="校验报告")

    # 控制字段
    error_message: str | None = Field(default=None, description="错误信息")
    pause_requested: bool = Field(default=False, description="是否请求暂停")
    user_responses: list[dict] = Field(default_factory=list, description="用户回复")

    # 多 Agent 协作字段 (DeerFlow 2.0 新增)
    task_decomposition: dict | None = Field(default=None, description="任务拆解结果")
    subtask_results: dict = Field(default_factory=dict, description="子任务结果映射 {task_id: result}")
    active_agents: list[str] = Field(default_factory=list, description="当前活跃的 Agent ID")
    coordinator_summary: str = Field(default="", description="Coordinator 汇总结果")

    def update_status(self, status: WorkflowStatus) -> None:
        """更新工作流状态"""
        self.workflow_run.update_status(status)

    def to_dict(self) -> dict:
        """转换为字典（用于 LangGraph 状态传递）"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowState":
        """从字典恢复状态"""
        return cls.model_validate(data)
