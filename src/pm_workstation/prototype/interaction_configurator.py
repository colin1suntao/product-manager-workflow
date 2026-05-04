"""交互配置器

为原型页面配置交互行为和事件绑定。
"""

from pydantic import BaseModel, Field

from pm_workstation.models.core import FlowStep, UserFlow


class Interaction(BaseModel):
    """交互定义"""
    trigger: str = Field(..., description="触发条件 (click, hover, submit, change)")
    target: str = Field(..., description="目标元素选择器")
    action: str = Field(..., description="执行动作 (navigate, open-modal, submit-form, toggle)")
    params: dict = Field(default_factory=dict, description="动作参数")
    description: str = Field(default="", description="交互描述")


class PageInteraction(BaseModel):
    """页面交互配置"""
    page_id: str = Field(..., description="页面ID")
    interactions: list[Interaction] = Field(default_factory=list, description="交互列表")


class InteractionConfigurator:
    """交互配置器
    
    根据用户流程和操作分支，为页面生成交互配置。
    """
    
    def configure_for_flow(self, flow: UserFlow, page_id: str) -> PageInteraction:
        """为用户流程配置交互
        
        Args:
            flow: 用户流程
            page_id: 页面ID
            
        Returns:
            页面交互配置
        """
        interactions = []
        
        for step in flow.steps:
            interaction = self._step_to_interaction(step, page_id)
            if interaction:
                interactions.append(interaction)
        
        # 添加分支交互
        for branch in flow.branches:
            branch_interaction = self._branch_to_interaction(branch, page_id)
            if branch_interaction:
                interactions.append(branch_interaction)
        
        return PageInteraction(
            page_id=page_id,
            interactions=interactions,
        )
    
    def configure_for_operations(
        self,
        operations: list[str],
        page_id: str,
    ) -> list[Interaction]:
        """为操作列表配置交互
        
        Args:
            operations: 操作列表
            page_id: 页面ID
            
        Returns:
            交互列表
        """
        interactions = []
        
        for operation in operations:
            interaction = self._operation_to_interaction(operation, page_id)
            interactions.append(interaction)
        
        return interactions
    
    def _step_to_interaction(
        self,
        step: FlowStep,
        page_id: str,
    ) -> Interaction | None:
        """将流程步骤转换为交互"""
        action_lower = step.action.lower() if step.action else ""
        
        # 根据动作类型推断交互
        if any(kw in action_lower for kw in ["click", "点击", "submit", "提交", "save", "保存"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-btn-{step.step_number}",
                action=self._infer_action_from_step(step),
                params={"step": step.step_number},
                description=step.description,
            )
        elif any(kw in action_lower for kw in ["input", "输入", "fill", "填写", "type"]):
            return Interaction(
                trigger="change",
                target=f"#{page_id}-input-{step.step_number}",
                action="update-field",
                params={"step": step.step_number},
                description=step.description,
            )
        elif any(kw in action_lower for kw in ["navigate", "跳转", "go to", "前往"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-nav-{step.step_number}",
                action="navigate",
                params={"target": step.expected_result},
                description=step.description,
            )
        
        # 默认交互
        return Interaction(
            trigger="click",
            target=f"#{page_id}-action-{step.step_number}",
            action="custom",
            params={"step": step.step_number},
            description=step.description,
        )
    
    def _branch_to_interaction(self, branch, page_id: str) -> Interaction | None:
        """将分支转换为交互"""
        if not hasattr(branch, 'name') or not hasattr(branch, 'condition'):
            return None
        
        return Interaction(
            trigger="click",
            target=f"#{page_id}-branch-{branch.name.lower().replace(' ', '-')}",
            action="show-branch",
            params={"branch": branch.name},
            description=f"分支：{branch.name}",
        )
    
    def _operation_to_interaction(
        self,
        operation: str,
        page_id: str,
    ) -> Interaction:
        """将操作转换为交互"""
        operation_lower = operation.lower()
        
        if any(kw in operation_lower for kw in ["列表", "list", "table"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-table-row",
                action="select-row",
                description=operation,
            )
        elif any(kw in operation_lower for kw in ["搜索", "search"]):
            return Interaction(
                trigger="change",
                target=f"#{page_id}-search-input",
                action="filter-data",
                description=operation,
            )
        elif any(kw in operation_lower for kw in ["创建", "create", "新建"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-create-btn",
                action="open-modal",
                params={"modal": "create-form"},
                description=operation,
            )
        elif any(kw in operation_lower for kw in ["编辑", "edit"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-edit-btn",
                action="open-modal",
                params={"modal": "edit-form"},
                description=operation,
            )
        elif any(kw in operation_lower for kw in ["删除", "delete"]):
            return Interaction(
                trigger="click",
                target=f"#{page_id}-delete-btn",
                action="confirm-dialog",
                params={"confirm": "确定删除？"},
                description=operation,
            )
        
        return Interaction(
            trigger="click",
            target=f"#{page_id}-action-btn",
            action="custom",
            description=operation,
        )
    
    def _infer_action_from_step(self, step: FlowStep) -> str:
        """从步骤推断动作类型"""
        action_lower = step.action.lower() if step.action else ""
        description_lower = step.description.lower() if step.description else ""
        combined = f"{action_lower} {description_lower}"
        
        if any(kw in combined for kw in ["submit", "提交", "save", "保存"]):
            return "submit-form"
        elif any(kw in combined for kw in ["navigate", "跳转", "go to"]):
            return "navigate"
        elif any(kw in combined for kw in ["open", "打开", "show", "显示"]):
            return "open-modal"
        elif any(kw in combined for kw in ["delete", "删除", "remove"]):
            return "confirm-dialog"
        
        return "custom"
