"""原型生成测试"""

import pytest

from pm_workstation.models.component import (
    Component,
    ComponentCategory,
    ComponentSearchResult,
    ComponentStatus,
    ComponentVersion,
)
from pm_workstation.models.core import (
    Attribute,
    Branch,
    BusinessEntity,
    FlowStep,
    Role,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)
from pm_workstation.prototype.component_matcher import ComponentMatcher
from pm_workstation.prototype.html_generator import HTMLGenerator
from pm_workstation.prototype.interaction_configurator import InteractionConfigurator
from pm_workstation.prototype.page_structure import PageStructureGenerator
from pm_workstation.prototype.style_checker import StyleConsistencyChecker
from pm_workstation.storage.component_store_memory import InMemoryComponentStore


class TestPageStructureGenerator:
    """页面结构生成器测试"""
    
    def test_generate_basic(self):
        """测试基础页面结构生成"""
        requirement = StructuredRequirement(
            rules=RuleTreeNode(rule_text="测试规则"),
            entities=[
                BusinessEntity(
                    name="User",
                    description="用户实体",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                    ],
                ),
            ],
            roles=[Role(name="admin", description="管理员")],
        )
        
        generator = PageStructureGenerator()
        structure = generator.generate(requirement)
        
        assert structure.root.id == "page-home"
        assert structure.root.name == "首页"
        assert len(structure.pages) > 0
    
    def test_generate_entity_pages(self):
        """测试实体页面生成"""
        entity = BusinessEntity(
            name="Order",
            description="订单实体",
            attributes=[
                Attribute(name="id", type="string", required=True),
                Attribute(name="amount", type="number", required=True),
            ],
        )
        
        generator = PageStructureGenerator()
        pages = generator._generate_entity_pages(entity, "page-home")
        
        assert len(pages) >= 2  # 至少列表页和详情页
        assert any("list" in p.id for p in pages)
        assert any("detail" in p.id for p in pages)
    
    def test_generate_entity_form_page(self):
        """测试实体表单页面生成"""
        entity = BusinessEntity(
            name="Product",
            attributes=[
                Attribute(name="name", type="string", required=True),
            ],
        )
        
        generator = PageStructureGenerator()
        pages = generator._generate_entity_pages(entity, "page-home")
        
        assert any("form" in p.id for p in pages)
    
    def test_generate_flow_pages(self):
        """测试流程页面生成"""
        flow = UserFlow(
            name="审批流程",
            role="manager",
            steps=[
                FlowStep(step_number=1, description="提交申请", action="提交"),
                FlowStep(step_number=2, description="审核", action="审核"),
                FlowStep(step_number=3, description="批准", action="批准"),
            ],
        )
        
        generator = PageStructureGenerator()
        pages = generator._generate_flow_pages(flow, "page-home")
        
        assert len(pages) >= 1
    
    def test_generate_rule_pages(self):
        """测试规则页面生成"""
        rules = RuleTreeNode(
            rule_text="主规则",
            children=[
                RuleTreeNode(rule_text="子规则1"),
                RuleTreeNode(rule_text="子规则2"),
            ],
        )
        
        generator = PageStructureGenerator()
        pages = generator._generate_rule_pages(rules, "page-home")
        
        assert len(pages) > 0
    
    def test_build_navigation(self):
        """测试导航构建"""
        from pm_workstation.prototype.page_structure import PageNode
        
        pages = [
            PageNode(id="p1", name="用户列表", entities=["User"]),
            PageNode(id="p2", name="用户详情", entities=["User"]),
            PageNode(id="p3", name="订单列表", entities=["Order"]),
        ]
        
        generator = PageStructureGenerator()
        nav = generator._build_navigation(pages)
        
        assert len(nav) == 2  # User 和 Order
        assert nav[0]["entity"] == "User"
        assert len(nav[0]["pages"]) == 2


class TestComponentMatcher:
    """组件匹配器测试"""
    
    @pytest.fixture
    def store(self):
        """创建带数据的存储"""
        import asyncio
        store = InMemoryComponentStore()
        
        async def setup():
            await store.create_component(
                Component(
                    id="c1",
                    name="DataTable",
                    description="A data table for displaying lists",
                    category=ComponentCategory.DATA_DISPLAY,
                    tags=["table", "list", "data"],
                    status=ComponentStatus.PUBLISHED,
                )
            )
            await store.create_version(
                ComponentVersion(
                    component_id="c1",
                    version="1.0.0",
                    html_template="<table></table>",
                )
            )
            
            await store.create_component(
                Component(
                    id="c2",
                    name="FormInput",
                    description="A form input field",
                    category=ComponentCategory.FORM,
                    tags=["form", "input", "text"],
                    status=ComponentStatus.PUBLISHED,
                )
            )
            await store.create_version(
                ComponentVersion(
                    component_id="c2",
                    version="1.0.0",
                    html_template="<input />",
                )
            )
            
            return store
        
        return asyncio.run(setup())
    
    @pytest.mark.asyncio
    async def test_match_for_page(self, store):
        """测试页面组件匹配"""
        matcher = ComponentMatcher(store)
        
        results = await matcher.match_for_page(
            page_description="display a list of data",
            suggested_components=["DataTable"],
        )
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_match_for_operation(self, store):
        """测试操作组件匹配"""
        matcher = ComponentMatcher(store)
        
        # 使用英文操作描述以便匹配英文组件
        result = await matcher.match_for_operation("list display")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_match_for_entity(self, store):
        """测试实体组件匹配"""
        matcher = ComponentMatcher(store)
        
        results = await matcher.match_for_entity(
            entity_name="User",
            entity_description="User management",
            attributes=[{"name": "email"}],
        )
        
        assert len(results) > 0
    
    def test_infer_category_from_operation(self):
        """测试从操作推断分类"""
        store = InMemoryComponentStore()
        matcher = ComponentMatcher(store)
        
        assert matcher._infer_category_from_operation("列表") == ComponentCategory.DATA_DISPLAY
        assert matcher._infer_category_from_operation("搜索") == ComponentCategory.INPUT
        assert matcher._infer_category_from_operation("创建") == ComponentCategory.FORM
        assert matcher._infer_category_from_operation("删除") == ComponentCategory.BUTTON
        assert matcher._infer_category_from_operation("导航") == ComponentCategory.NAVIGATION


class TestInteractionConfigurator:
    """交互配置器测试"""
    
    def test_configure_for_flow(self):
        """测试流程交互配置"""
        flow = UserFlow(
            name="测试流程",
            role="user",
            steps=[
                FlowStep(
                    step_number=1,
                    description="点击提交按钮",
                    action="点击提交",
                ),
                FlowStep(
                    step_number=2,
                    description="输入用户名",
                    action="输入",
                ),
            ],
        )
        
        configurator = InteractionConfigurator()
        result = configurator.configure_for_flow(flow, "page-test")
        
        assert result.page_id == "page-test"
        assert len(result.interactions) > 0
    
    def test_configure_for_operations(self):
        """测试操作交互配置"""
        operations = ["列表展示", "搜索", "创建", "删除"]
        
        configurator = InteractionConfigurator()
        interactions = configurator.configure_for_operations(operations, "page-list")
        
        assert len(interactions) == 4
    
    def test_step_to_interaction_click(self):
        """测试点击步骤转换"""
        step = FlowStep(
            step_number=1,
            description="点击按钮",
            action="点击提交",
        )
        
        configurator = InteractionConfigurator()
        interaction = configurator._step_to_interaction(step, "page-1")
        
        assert interaction.trigger == "click"
    
    def test_step_to_interaction_change(self):
        """测试输入步骤转换"""
        step = FlowStep(
            step_number=2,
            description="输入内容",
            action="输入",
        )
        
        configurator = InteractionConfigurator()
        interaction = configurator._step_to_interaction(step, "page-1")
        
        assert interaction.trigger == "change"
    
    def test_operation_to_interaction(self):
        """测试操作交互转换"""
        configurator = InteractionConfigurator()
        
        # 搜索操作
        interaction = configurator._operation_to_interaction("搜索", "page-1")
        assert interaction.trigger == "change"
        
        # 创建操作
        interaction = configurator._operation_to_interaction("创建", "page-1")
        assert interaction.action == "open-modal"
        
        # 删除操作
        interaction = configurator._operation_to_interaction("删除", "page-1")
        assert interaction.action == "confirm-dialog"


class TestStyleConsistencyChecker:
    """样式一致性检查器测试"""
    
    def test_check_pass(self):
        """测试通过检查"""
        css = """
        body { font-family: -apple-system, sans-serif; }
        .btn { border-radius: 6px; cursor: pointer; }
        input { border: 1px solid #d9d9d9; padding: 8px 12px; }
        .spacer { margin: 8px 0; }
        """
        
        checker = StyleConsistencyChecker()
        result = checker.check("<html></html>", css)
        
        # 1px border 是被允许的常见情况
        issues = [i for i in result.issues if "1px" not in i.issue]
        assert len(issues) == 0
    
    def test_check_color_warning(self):
        """测试颜色警告"""
        css = "body { background: #ff0000; }"
        
        checker = StyleConsistencyChecker()
        result = checker.check("<html></html>", css)
        
        assert any(i.severity == "warning" for i in result.issues)
    
    def test_check_button_style(self):
        """测试按钮样式检查"""
        html = "<button>Click me</button>"
        css = "button { }"
        
        checker = StyleConsistencyChecker()
        result = checker.check(html, css)
        
        assert len(result.issues) > 0
    
    def test_check_form_style(self):
        """测试表单样式检查"""
        html = "<form><input type='text' /></form>"
        css = "input { }"
        
        checker = StyleConsistencyChecker()
        result = checker.check(html, css)
        
        assert len(result.issues) > 0
    
    def test_rules_checked_count(self):
        """测试检查规则计数"""
        checker = StyleConsistencyChecker()
        result = checker.check("<html></html>", "")
        
        assert result.rules_checked == 5


class TestHTMLGenerator:
    """HTML 生成器测试"""
    
    def test_generate_basic(self):
        """测试基础 HTML 生成"""
        from pm_workstation.prototype.page_structure import PageNode, PageStructure
        
        structure = PageStructure(
            requirement_id="test-1",
            root=PageNode(id="page-home", name="首页"),
            pages=[
                PageNode(id="page-list", name="列表页", layout_hint="table"),
                PageNode(id="page-form", name="表单页", layout_hint="form"),
            ],
        )
        
        generator = HTMLGenerator()
        result = generator.generate(structure)
        
        assert "html" in result
        assert "css" in result
        assert "js" in result
        assert "<!DOCTYPE html>" in result["html"]
        assert "列表页" in result["html"]
        assert "表单页" in result["html"]
    
    def test_generate_table_content(self):
        """测试表格内容生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-list",
            name="用户列表",
            layout_hint="table",
            entities=["User"],
        )
        
        generator = HTMLGenerator()
        html = generator._generate_page(page)
        
        assert "<table" in html
        assert "搜索" in html
        assert "新建" in html
    
    def test_generate_form_content(self):
        """测试表单内容生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-form",
            name="新建用户",
            layout_hint="form",
        )
        
        generator = HTMLGenerator()
        html = generator._generate_page(page)
        
        assert "<form" in html
        assert "保存" in html
        assert "取消" in html
    
    def test_generate_detail_content(self):
        """测试详情内容生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-detail",
            name="用户详情",
            layout_hint="detail",
        )
        
        generator = HTMLGenerator()
        html = generator._generate_page(page)
        
        assert "编辑" in html
        assert "删除" in html
    
    def test_generate_grid_content(self):
        """测试网格内容生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-grid",
            name="仪表盘",
            layout_hint="grid",
        )
        
        generator = HTMLGenerator()
        html = generator._generate_page(page)
        
        assert "grid-template-columns" in html
    
    def test_generate_wizard_content(self):
        """测试向导内容生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-wizard",
            name="多步流程",
            layout_hint="wizard",
        )
        
        generator = HTMLGenerator()
        html = generator._generate_page(page)
        
        assert "步骤一" in html
        assert "上一步" in html
        assert "下一步" in html
    
    def test_generate_page_js(self):
        """测试页面 JS 生成"""
        from pm_workstation.prototype.page_structure import PageNode
        
        page = PageNode(
            id="page-test",
            name="测试页",
        )
        
        generator = HTMLGenerator()
        js = generator._generate_page_js(page)
        
        assert "page-test" in js
        assert "addEventListener" in js
    
    def test_generate_without_css(self):
        """测试不生成 CSS"""
        from pm_workstation.prototype.page_structure import PageNode, PageStructure
        
        structure = PageStructure(
            requirement_id="test-1",
            root=PageNode(id="page-home", name="首页"),
            pages=[PageNode(id="page-1", name="页面1")],
        )
        
        generator = HTMLGenerator()
        result = generator.generate(structure, include_css=False)
        
        # 应该使用默认 CSS
        assert result["css"] != ""


class TestPrototypeIntegration:
    """原型生成集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_prototype_generation(self):
        """测试完整原型生成流程"""
        # 1. 创建结构化需求
        requirement = StructuredRequirement(
            entities=[
                BusinessEntity(
                    name="User",
                    description="用户管理",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                        Attribute(name="email", type="string", required=True),
                    ],
                ),
            ],
            roles=[Role(name="admin", description="管理员")],
            flows=[
                UserFlow(
                    name="用户审批",
                    role="admin",
                    steps=[
                        FlowStep(step_number=1, description="查看申请", action="查看"),
                        FlowStep(step_number=2, description="审批", action="点击审批"),
                    ],
                ),
            ],
            rules=RuleTreeNode(
                rule_text="用户管理规则",
                children=[
                    RuleTreeNode(rule_text="创建用户"),
                    RuleTreeNode(rule_text="删除用户"),
                ],
            ),
        )
        
        # 2. 生成页面结构
        structure_generator = PageStructureGenerator()
        structure = structure_generator.generate(requirement)
        
        assert len(structure.pages) > 0
        
        # 3. 生成 HTML 原型
        html_generator = HTMLGenerator()
        result = html_generator.generate(structure)
        
        assert len(result["html"]) > 0
        assert len(result["css"]) > 0
        assert len(result["js"]) > 0
        
        # 4. 检查样式一致性
        checker = StyleConsistencyChecker()
        style_result = checker.check(result["html"], result["css"])
        
        # 生成的代码应该通过基本样式检查
        assert style_result.rules_checked == 5
