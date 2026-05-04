"""页面结构生成器

从结构化需求生成页面结构树，用于原型生成。
"""

from typing import Optional

from pydantic import BaseModel, Field

from pm_workstation.models.core import (
    BusinessEntity,
    FlowStep,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)


class PageNode(BaseModel):
    """页面节点"""
    id: str = Field(..., description="节点唯一标识")
    name: str = Field(..., description="节点名称")
    page_type: str = Field(default="page", description="页面类型 (page, modal, sidebar, header, footer)")
    description: str = Field(default="", description="页面描述")
    parent_id: Optional[str] = Field(default=None, description="父节点ID")
    children: list["PageNode"] = Field(default_factory=list, description="子页面")
    
    # 页面内容
    entities: list[str] = Field(default_factory=list, description="相关实体")
    operations: list[str] = Field(default_factory=list, description="操作列表")
    flow_steps: list[str] = Field(default_factory=list, description="关联流程步骤")
    
    # 组件信息
    suggested_components: list[str] = Field(default_factory=list, description="建议组件")
    layout_hint: str = Field(default="", description="布局提示")


class PageStructure(BaseModel):
    """页面结构"""
    requirement_id: str = Field(..., description="需求ID")
    root: PageNode = Field(..., description="根页面节点")
    pages: list[PageNode] = Field(default_factory=list, description="所有页面节点")
    navigation: list[dict] = Field(default_factory=list, description="导航结构")


class PageStructureGenerator:
    """页面结构生成器
    
    根据结构化需求自动生成页面结构树。
    """
    
    def generate(self, requirement: StructuredRequirement) -> PageStructure:
        """生成页面结构
        
        Args:
            requirement: 结构化需求
            
        Returns:
            页面结构
        """
        root = self._generate_root(requirement)
        pages = self._extract_pages(requirement, root.id)
        navigation = self._build_navigation(pages)
        
        return PageStructure(
            requirement_id=str(id(requirement)),
            root=root,
            pages=pages,
            navigation=navigation,
        )
    
    def _generate_root(self, requirement: StructuredRequirement) -> PageNode:
        """生成根节点（首页/仪表盘）"""
        entity_names = [e.name for e in requirement.entities]
        role_names = [r.name for r in requirement.roles]
        
        return PageNode(
            id="page-home",
            name="首页",
            page_type="page",
            description="系统首页，展示核心功能入口",
            entities=entity_names,
            operations=["导航", "概览"],
            suggested_components=["Navigation", "Dashboard", "Card"],
            layout_hint="grid",
        )
    
    def _extract_pages(
        self,
        requirement: StructuredRequirement,
        root_id: str,
    ) -> list[PageNode]:
        """从需求中提取页面"""
        pages = []
        
        # 从实体生成 CRUD 页面
        for entity in requirement.entities:
            entity_pages = self._generate_entity_pages(entity, root_id)
            pages.extend(entity_pages)
        
        # 从用户流程生成页面
        for flow in requirement.flows:
            flow_pages = self._generate_flow_pages(flow, root_id)
            pages.extend(flow_pages)
        
        # 从规则树生成页面
        rule_pages = self._generate_rule_pages(requirement.rules, root_id)
        pages.extend(rule_pages)
        
        return pages
    
    def _generate_entity_pages(
        self,
        entity: BusinessEntity,
        parent_id: str,
    ) -> list[PageNode]:
        """为实体生成 CRUD 页面"""
        pages = []
        
        # 列表页
        list_page = PageNode(
            id=f"page-{entity.name.lower()}-list",
            name=f"{entity.name}列表",
            page_type="page",
            description=f"{entity.description or entity.name}的列表展示页面",
            parent_id=parent_id,
            entities=[entity.name],
            operations=["列表展示", "搜索", "筛选", "分页"],
            flow_steps=[f"查看{entity.name}列表"],
            suggested_components=["DataTable", "SearchBar", "Pagination", "Toolbar"],
            layout_hint="table",
        )
        pages.append(list_page)
        
        # 详情页
        detail_page = PageNode(
            id=f"page-{entity.name.lower()}-detail",
            name=f"{entity.name}详情",
            page_type="page",
            description=f"{entity.name}的详细信息展示页面",
            parent_id=parent_id,
            entities=[entity.name],
            operations=["查看详情", "编辑", "删除"],
            flow_steps=[f"查看{entity.name}详情"],
            suggested_components=["DetailPanel", "Form", "Button", "Breadcrumb"],
            layout_hint="detail",
        )
        pages.append(detail_page)
        
        # 如果有必填属性，生成创建/编辑表单页
        required_attrs = [a for a in entity.attributes if a.required]
        if required_attrs:
            form_page = PageNode(
                id=f"page-{entity.name.lower()}-form",
                name=f"新建/编辑{entity.name}",
                page_type="page",
                description=f"{entity.name}的创建和编辑表单",
                parent_id=parent_id,
                entities=[entity.name],
                operations=["创建", "编辑", "保存", "取消"],
                flow_steps=[f"创建{entity.name}", f"编辑{entity.name}"],
                suggested_components=["Form", "Input", "Select", "Button", "Modal"],
                layout_hint="form",
            )
            pages.append(form_page)
        
        return pages
    
    def _generate_flow_pages(
        self,
        flow: UserFlow,
        parent_id: str,
    ) -> list[PageNode]:
        """从用户流程生成页面"""
        pages = []
        
        # 为复杂流程生成专用页面
        if len(flow.steps) >= 3:
            flow_page = PageNode(
                id=f"page-flow-{flow.name.lower().replace(' ', '-')}",
                name=flow.name,
                page_type="page",
                description=f"流程页面：{flow.name}",
                parent_id=parent_id,
                operations=[step.action for step in flow.steps if step.action],
                flow_steps=[step.description for step in flow.steps],
                suggested_components=["Steps", "Form", "Button"],
                layout_hint="wizard",
            )
            pages.append(flow_page)
        
        return pages
    
    def _generate_rule_pages(
        self,
        rules: RuleTreeNode,
        parent_id: str,
        depth: int = 0,
    ) -> list[PageNode]:
        """从规则树生成页面"""
        pages = []
        
        # 仅为顶层规则生成页面提示
        if depth <= 1 and rules.children:
            for child in rules.children[:3]:  # 限制子规则数量
                rule_page = PageNode(
                    id=f"page-rule-{id(child)}",
                    name=child.rule_text[:30] + ("..." if len(child.rule_text) > 30 else ""),
                    page_type="page",
                    description=child.rule_text,
                    parent_id=parent_id,
                    operations=[a.description for a in child.actions if a.description],
                    suggested_components=["Alert", "Card", "Form"],
                    layout_hint="card",
                )
                pages.append(rule_page)
        
        return pages
    
    def _build_navigation(self, pages: list[PageNode]) -> list[dict]:
        """构建导航结构"""
        nav_items = []
        
        # 按实体分组的页面
        entities_seen = set()
        for page in pages:
            for entity in page.entities:
                if entity not in entities_seen:
                    entities_seen.add(entity)
                    entity_pages = [p for p in pages if entity in p.entities]
                    nav_items.append({
                        "entity": entity,
                        "pages": [
                            {"id": p.id, "name": p.name}
                            for p in entity_pages
                        ],
                    })
        
        return nav_items
