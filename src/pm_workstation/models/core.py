"""核心数据模型定义"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    INIT = "init"
    PARSING = "parsing"
    PARSED = "parsed"
    GENERATING = "generating"
    GENERATED = "generated"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_USER_INPUT = "waiting_user_input"
    CANCELLED = "cancelled"


class Attribute(BaseModel):
    """业务实体属性"""
    name: str = Field(..., description="属性名称")
    type: str = Field(..., description="属性类型")
    description: str = Field(default="", description="属性描述")
    required: bool = Field(default=False, description="是否必需")


class Relationship(BaseModel):
    """业务实体关联关系"""
    target_entity: str = Field(..., description="目标实体名称")
    relationship_type: str = Field(..., description="关系类型 (one-to-one, one-to-many, many-to-many)")
    description: str = Field(default="", description="关系描述")


class BusinessEntity(BaseModel):
    """业务实体"""
    name: str = Field(..., description="实体名称")
    description: str = Field(default="", description="实体描述")
    attributes: list[Attribute] = Field(default_factory=list, description="属性列表")
    relationships: list[Relationship] = Field(default_factory=list, description="关联关系")


class Condition(BaseModel):
    """业务规则条件"""
    field: str = Field(..., description="条件字段")
    operator: str = Field(..., description="操作符 (==, !=, >, <, >=, <=, in, contains)")
    value: str = Field(..., description="条件值")


class Action(BaseModel):
    """业务规则执行动作"""
    action_type: str = Field(..., description="动作类型")
    description: str = Field(default="", description="动作描述")
    parameters: dict = Field(default_factory=dict, description="动作参数")


class RuleTreeNode(BaseModel):
    """业务规则树节点"""
    rule_text: str = Field(..., description="规则描述")
    conditions: list[Condition] = Field(default_factory=list, description="条件列表")
    actions: list[Action] = Field(default_factory=list, description="执行动作")
    children: list["RuleTreeNode"] = Field(default_factory=list, description="子规则")
    depth: int = Field(default=0, description="规则深度")


class FlowStep(BaseModel):
    """流程步骤"""
    step_number: int = Field(..., description="步骤序号")
    description: str = Field(..., description="步骤描述")
    action: str = Field(default="", description="用户操作")
    expected_result: str = Field(default="", description="预期结果")


class Branch(BaseModel):
    """操作分支"""
    name: str = Field(..., description="分支名称")
    branch_type: str = Field(..., description="分支类型 (normal, exception, boundary)")
    condition: str = Field(default="", description="触发条件")
    steps: list[FlowStep] = Field(default_factory=list, description="分支步骤")


class EdgeCase(BaseModel):
    """边界场景"""
    description: str = Field(..., description="场景描述")
    condition: str = Field(..., description="触发条件")
    expected_behavior: str = Field(..., description="预期行为")


class Role(BaseModel):
    """用户角色"""
    name: str = Field(..., description="角色名称")
    description: str = Field(default="", description="角色描述")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


class Question(BaseModel):
    """澄清问题"""
    question: str = Field(..., description="问题内容")
    context: str = Field(default="", description="问题上下文")
    options: list[str] = Field(default_factory=list, description="可选答案")


class UserFlow(BaseModel):
    """用户流程"""
    name: str = Field(..., description="流程名称")
    role: str = Field(..., description="执行角色")
    steps: list[FlowStep] = Field(default_factory=list, description="流程步骤")
    branches: list[Branch] = Field(default_factory=list, description="分支流程")
    entry_point: str = Field(default="", description="入口点")
    exit_points: list[str] = Field(default_factory=list, description="出口点")


class StructuredRequirement(BaseModel):
    """结构化需求"""
    entities: list[BusinessEntity] = Field(default_factory=list, description="业务实体")
    roles: list[Role] = Field(default_factory=list, description="用户角色")
    rules: RuleTreeNode = Field(..., description="业务规则树")
    flows: list[UserFlow] = Field(default_factory=list, description="用户操作流程")
    branches: list[Branch] = Field(default_factory=list, description="操作分支")
    edge_cases: list[EdgeCase] = Field(default_factory=list, description="边界场景")
    clarifications: list[Question] = Field(default_factory=list, description="待澄清问题")
    reasoning_trace: str = Field(default="", description="推理路径记录")


class VerificationReport(BaseModel):
    """校验报告"""
    report_id: str = Field(..., description="报告ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    prototype_issues: list[dict] = Field(default_factory=list, description="原型问题")
    document_issues: list[dict] = Field(default_factory=list, description="文档问题")
    consistency_issues: list[dict] = Field(default_factory=list, description="一致性问题")
    auto_fixed_issues: list[dict] = Field(default_factory=list, description="已自动修复的问题")
    manual_review_required: list[dict] = Field(default_factory=list, description="需要人工审查的问题")


class WorkflowRun(BaseModel):
    """工作流运行记录"""
    id: str = Field(..., description="唯一标识")
    user_id: str = Field(..., description="用户ID")
    requirement_text: str = Field(..., description="原始需求文本")
    status: WorkflowStatus = Field(default=WorkflowStatus.INIT, description="当前状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")
    structured_requirement: Optional[StructuredRequirement] = Field(default=None, description="结构化需求")
    prototype_url: Optional[str] = Field(default=None, description="原型访问URL")
    prd_document_url: Optional[str] = Field(default=None, description="PRD文档URL")
    verification_report: Optional[VerificationReport] = Field(default=None, description="校验报告")
    verification_report_url: Optional[str] = Field(default=None, description="校验报告URL")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    def update_status(self, status: WorkflowStatus):
        """更新工作流状态"""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
