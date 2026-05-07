"""文档结构生成器

从结构化需求生成文档结构树。
"""


from pydantic import BaseModel, Field

from pm_workstation.models.core import (
    BusinessEntity,
    Role,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)


class DocumentSection(BaseModel):
    """文档段落"""
    id: str = Field(..., description="段落唯一标识")
    title: str = Field(..., description="段落标题")
    level: int = Field(default=2, description="标题级别")
    content: str = Field(default="", description="段落内容")
    children: list["DocumentSection"] = Field(default_factory=list, description="子段落")
    metadata: dict = Field(default_factory=dict, description="元数据")


class DocumentStructureGenerator:
    """文档结构生成器

    根据结构化需求生成 PRD 文档的结构树，
    为后续的模板渲染提供内容骨架。
    """

    def generate(self, requirement: StructuredRequirement) -> list[DocumentSection]:
        """生成文档结构

        Args:
            requirement: 结构化需求

        Returns:
            文档段落列表
        """
        sections = []

        sections.append(self._generate_roles_section(requirement.roles))
        sections.append(self._generate_entities_section(requirement.entities))
        sections.append(self._generate_rules_section(requirement.rules))
        sections.append(self._generate_flows_section(requirement.flows))
        sections.append(self._generate_branches_section(requirement.branches))
        sections.append(self._generate_edge_cases_section(requirement.edge_cases))

        # 移除空段落
        return [s for s in sections if s.content or s.children]

    def _generate_roles_section(self, roles: list[Role]) -> DocumentSection:
        """生成用户角色段落"""
        if not roles:
            return DocumentSection(id="roles", title="用户角色", level=2)

        table_rows = ["| 角色 | 描述 |", "|------|------|"]
        for role in roles:
            table_rows.append(f"| {role.name} | {role.description} |")

        return DocumentSection(
            id="roles",
            title="用户角色",
            level=2,
            content="\n".join(table_rows),
            metadata={"count": len(roles)},
        )

    def _generate_entities_section(self, entities: list[BusinessEntity]) -> DocumentSection:
        """生成业务实体段落"""
        if not entities:
            return DocumentSection(id="entities", title="业务实体", level=2)

        children = []
        for entity in entities:
            entity_section = self._generate_entity_section(entity)
            children.append(entity_section)

        return DocumentSection(
            id="entities",
            title="业务实体",
            level=2,
            children=children,
            metadata={"count": len(entities)},
        )

    def _generate_entity_section(self, entity: BusinessEntity) -> DocumentSection:
        """生成单个实体段落"""
        # 实体描述
        content = f"**{entity.name}**: {entity.description}" if entity.description else f"**{entity.name}**"

        # 属性表格
        if entity.attributes:
            attr_rows = ["| 属性 | 类型 | 描述 | 必需 |", "|------|------|------|------|"]
            for attr in entity.attributes:
                required_mark = "是" if attr.required else "否"
                attr_rows.append(
                    f"| {attr.name} | {attr.type} | {attr.description} | {required_mark} |"
                )
            content += "\n\n" + "\n".join(attr_rows)

        # 关联关系
        children = []
        if entity.relationships:
            rel_content = []
            for rel in entity.relationships:
                rel_content.append(
                    f"- **{rel.target_entity}**: {rel.relationship_type} - {rel.description}"
                )
            children.append(DocumentSection(
                id=f"entity-{entity.name.lower()}-relations",
                title="关联关系",
                level=4,
                content="\n".join(rel_content),
            ))

        return DocumentSection(
            id=f"entity-{entity.name.lower()}",
            title=entity.name,
            level=3,
            content=content,
            children=children,
        )

    def _generate_rules_section(self, rules: RuleTreeNode) -> DocumentSection:
        """生成业务规则段落"""
        if not rules.rule_text and not rules.children:
            return DocumentSection(id="rules", title="业务规则", level=2)

        content_parts = []
        if rules.rule_text:
            content_parts.append(f"**主规则**: {rules.rule_text}")

        children = []
        self._add_rule_children(rules, children, indent=0)

        content = "\n\n".join(content_parts) if content_parts else ""

        return DocumentSection(
            id="rules",
            title="业务规则",
            level=2,
            content=content,
            children=children,
            metadata={"rule_count": len(rules.children)},
        )

    def _add_rule_children(
        self,
        node: RuleTreeNode,
        children: list[DocumentSection],
        indent: int = 0,
    ):
        """递归添加规则子节点"""
        level = min(4, 3 + indent)  # H3, H4, H4...

        for child in node.children:
            rule_content = f"{child.rule_text}"

            if child.conditions:
                cond_parts = []
                for cond in child.conditions:
                    cond_parts.append(f"- 当 `{cond.field} {cond.operator} {cond.value}` 时")
                rule_content += "\n\n**条件**:\n" + "\n".join(cond_parts)

            if child.actions:
                action_parts = []
                for action in child.actions:
                    action_parts.append(f"- {action.action_type}: {action.description}")
                rule_content += "\n\n**动作**:\n" + "\n".join(action_parts)

            section = DocumentSection(
                id=f"rule-{id(child)}",
                title=child.rule_text[:50] + ("..." if len(child.rule_text) > 50 else ""),
                level=level,
                content=rule_content,
            )
            children.append(section)

            # 递归处理更深层次的子规则
            if child.children and indent < 2:
                self._add_rule_children(child, section.children, indent + 1)

    def _generate_flows_section(self, flows: list[UserFlow]) -> DocumentSection:
        """生成用户流程段落"""
        if not flows:
            return DocumentSection(id="flows", title="用户流程", level=2)

        children = []
        for flow in flows:
            flow_section = self._generate_flow_section(flow)
            children.append(flow_section)

        return DocumentSection(
            id="flows",
            title="用户流程",
            level=2,
            children=children,
            metadata={"flow_count": len(flows)},
        )

    def _generate_flow_section(self, flow: UserFlow) -> DocumentSection:
        """生成单个流程段落"""
        content_parts = [f"**执行角色**: {flow.role}"]

        if flow.entry_point:
            content_parts.append(f"**入口点**: {flow.entry_point}")

        # 流程步骤表格
        step_rows = ["| 步骤 | 描述 | 操作 | 预期结果 |", "|------|------|------|----------|"]
        for step in flow.steps:
            step_rows.append(
                f"| {step.step_number} | {step.description} | {step.action} | {step.expected_result} |"
            )
        content_parts.append("\n".join(step_rows))

        if flow.exit_points:
            content_parts.append(f"**出口点**: {', '.join(flow.exit_points)}")

        content = "\n\n".join(content_parts)

        return DocumentSection(
            id=f"flow-{flow.name.lower().replace(' ', '-')}",
            title=flow.name,
            level=3,
            content=content,
        )

    def _generate_branches_section(self, branches: list) -> DocumentSection:
        """生成分支段落"""
        if not branches:
            return DocumentSection(id="branches", title="操作分支", level=2)

        content_parts = []
        for branch in branches:
            name = getattr(branch, 'name', 'Unknown')
            condition = getattr(branch, 'condition', '')
            description = getattr(branch, 'description', '')

            content_parts.append(f"### {name}")
            if condition:
                content_parts.append(f"**条件**: {condition}")
            if description:
                content_parts.append(description)

        return DocumentSection(
            id="branches",
            title="操作分支",
            level=2,
            content="\n\n".join(content_parts),
            metadata={"branch_count": len(branches)},
        )

    def _generate_edge_cases_section(self, edge_cases: list) -> DocumentSection:
        """生成边界场景段落"""
        if not edge_cases:
            return DocumentSection(id="edge-cases", title="边界场景", level=2)

        content_parts = []
        for case in edge_cases:
            name = getattr(case, 'name', 'Unknown')
            description = getattr(case, 'description', '')
            handling = getattr(case, 'handling', '')

            content_parts.append(f"### {name}")
            if description:
                content_parts.append(f"**场景**: {description}")
            if handling:
                content_parts.append(f"**处理方式**: {handling}")

        return DocumentSection(
            id="edge-cases",
            title="边界场景",
            level=2,
            content="\n\n".join(content_parts),
            metadata={"edge_case_count": len(edge_cases)},
        )
