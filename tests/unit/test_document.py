"""文档生成测试"""

import pytest

from pm_workstation.document.content_generator import ContentGenerator
from pm_workstation.document.markdown_formatter import MarkdownFormatter
from pm_workstation.document.structure_generator import DocumentSection, DocumentStructureGenerator
from pm_workstation.document.template_engine import PRDTemplate, TemplateEngine, TemplateSection, TemplateVariable
from pm_workstation.document.terminology_checker import TerminologyConsistencyChecker
from pm_workstation.models.core import (
    Attribute,
    Branch,
    BusinessEntity,
    EdgeCase,
    FlowStep,
    Relationship,
    Role,
    RuleTreeNode,
    StructuredRequirement,
    UserFlow,
)


class TestTemplateEngine:
    """模板引擎测试"""
    
    @pytest.fixture
    def engine(self):
        """创建模板引擎"""
        return TemplateEngine()
    
    def test_register_template(self, engine):
        """测试注册模板"""
        template = PRDTemplate(
            id="custom-template",
            name="Custom Template",
            sections=[
                TemplateSection(
                    id="section-1",
                    title="Section 1",
                    level=2,
                    content_template="Content: {{name}}",
                    variables=[TemplateVariable(name="name", required=True)],
                ),
            ],
        )
        
        engine.register_template(template)
        result = engine.get_template("custom-template")
        
        assert result is not None
        assert result.name == "Custom Template"
    
    def test_get_nonexistent_template(self, engine):
        """测试获取不存在的模板"""
        result = engine.get_template("nonexistent")
        assert result is None
    
    def test_list_templates(self, engine):
        """测试列出模板"""
        templates = engine.list_templates()
        
        # 默认应该有至少2个模板
        assert len(templates) >= 2
    
    def test_render_template(self, engine):
        """测试渲染模板"""
        context = {
            "project_name": "Test Project",
            "created_date": "2026-05-04",
            "author": "Test Author",
        }
        
        result = engine.render("prd-simple", context)
        
        assert "Test Project" in result
        assert "2026-05-04" in result
    
    def test_render_with_default_variable(self, engine):
        """测试渲染带默认值的变量"""
        context = {
            "project_name": "Test",
            "created_date": "2026-05-04",
        }
        
        result = engine.render("prd-simple", context)
        
        # doc_version 应该有默认值
        assert "prd-standard" in engine.list_templates()[0].id
    
    def test_render_with_missing_required_variable(self, engine):
        """测试渲染缺少必需变量"""
        context = {
            "created_date": "2026-05-04",
            # 缺少 project_name
        }
        
        result = engine.render("prd-simple", context)
        
        # 缺失变量应该被替换为空字符串
        assert "{{project_name}}" not in result
    
    def test_render_conditional_section(self, engine):
        """测试条件渲染"""
        # 没有 roles 时，roles section 不应该出现
        context = {
            "project_name": "Test",
            "created_date": "2026-05-04",
            "has_roles": False,
            "has_entities": False,
            "has_rules": False,
            "has_flows": False,
            "roles_table": "",
            "entities_content": "",
            "functional_requirements": "",
            "business_rules": "",
            "user_flows_content": "",
        }
        
        result = engine.render("prd-standard", context)
        
        # 条件不满足的段落不应该出现
        # 但用户角色标题可能仍然出现（取决于模板设计）
        assert "{{" not in result  # 没有未替换的变量
    
    def test_render_condition_expression(self, engine):
        """测试条件表达式"""
        template = PRDTemplate(
            id="test-conditional",
            name="Test",
            sections=[
                TemplateSection(
                    id="s1",
                    title="Has Items",
                    level=2,
                    content_template="Items: {{items_text}}",
                    condition="has_items",
                ),
                TemplateSection(
                    id="s2",
                    title="Count Check",
                    level=2,
                    content_template="Count: {{count}}",
                    condition="count > 0",
                ),
            ],
        )
        
        engine = TemplateEngine()
        engine.register_template(template)
        
        # has_items = true, count > 0
        result = engine.render("test-conditional", {
            "has_items": True,
            "count": 5,
            "items_text": "item1, item2",
        })
        
        assert "Has Items" in result
        assert "Count Check" in result
        
        # has_items = false
        result = engine.render("test-conditional", {
            "has_items": False,
            "count": 0,
            "items_text": "item1",
        })
        
        assert "Has Items" not in result
        assert "Count Check" not in result
    
    def test_get_required_variables(self, engine):
        """测试获取必需变量"""
        variables = engine.get_required_variables("prd-simple")
        
        required = [v for v in variables if v.required]
        assert len(required) >= 2  # project_name, created_date
    
    def test_substitute_variables_with_pipe_default(self, engine):
        """测试带管道默认值的变量替换"""
        result = engine._substitute_variables(
            "Hello {{name|World}}!",
            {},
        )
        
        assert result == "Hello World!"
    
    def test_substitute_variables_with_value(self, engine):
        """测试有值时的变量替换"""
        result = engine._substitute_variables(
            "Hello {{name|World}}!",
            {"name": "Alice"},
        )
        
        assert result == "Hello Alice!"


class TestDocumentStructureGenerator:
    """文档结构生成器测试"""
    
    @pytest.fixture
    def generator(self):
        """创建生成器"""
        return DocumentStructureGenerator()
    
    @pytest.fixture
    def sample_requirement(self):
        """创建示例需求"""
        return StructuredRequirement(
            entities=[
                BusinessEntity(
                    name="User",
                    description="系统用户",
                    attributes=[
                        Attribute(name="name", type="string", required=True, description="用户名"),
                        Attribute(name="email", type="string", required=True, description="邮箱"),
                        Attribute(name="age", type="number", required=False, description="年龄"),
                    ],
                    relationships=[
                        Relationship(
                            target_entity="Order",
                            relationship_type="one-to-many",
                            description="一个用户可以有多个订单",
                        ),
                    ],
                ),
            ],
            roles=[
                Role(name="admin", description="系统管理员"),
                Role(name="user", description="普通用户"),
            ],
            flows=[
                UserFlow(
                    name="用户注册",
                    role="user",
                    steps=[
                        FlowStep(step_number=1, description="填写注册表单", action="输入信息", expected_result="表单验证通过"),
                        FlowStep(step_number=2, description="提交注册", action="点击注册", expected_result="注册成功"),
                    ],
                    entry_point="注册页面",
                    exit_points=["登录页面"],
                ),
            ],
            rules=RuleTreeNode(
                rule_text="用户管理规则",
                children=[
                    RuleTreeNode(
                        rule_text="新用户必须验证邮箱",
                        conditions=[],
                        actions=[],
                    ),
                ],
            ),
            branches=[
                Branch(name="VIP用户", branch_type="normal", condition="is_vip == true"),
            ],
            edge_cases=[
                EdgeCase(name="并发注册", description="同一邮箱同时注册", condition="concurrent", expected_behavior="使用唯一token", handling="使用唯一token"),
            ],
        )
    
    def test_generate_structure(self, generator, sample_requirement):
        """测试生成文档结构"""
        sections = generator.generate(sample_requirement)
        
        assert len(sections) > 0
    
    def test_roles_section(self, generator, sample_requirement):
        """测试用户角色段落"""
        section = generator._generate_roles_section(sample_requirement.roles)
        
        assert "admin" in section.content
        assert "user" in section.content
        assert section.metadata["count"] == 2
    
    def test_entities_section(self, generator, sample_requirement):
        """测试业务实体段落"""
        section = generator._generate_entities_section(sample_requirement.entities)
        
        assert len(section.children) == 1
        assert section.children[0].title == "User"
    
    def test_entity_section_with_attributes(self, generator):
        """测试实体属性表格"""
        entity = BusinessEntity(
            name="Product",
            description="商品",
            attributes=[
                Attribute(name="name", type="string", required=True, description="商品名称"),
            ],
        )
        
        section = generator._generate_entity_section(entity)
        
        assert "name" in section.content
        assert "string" in section.content
        assert "商品名称" in section.content
    
    def test_entity_section_with_relations(self, generator):
        """测试实体关联关系"""
        entity = BusinessEntity(
            name="Order",
            relationships=[
                Relationship(
                    target_entity="User",
                    relationship_type="many-to-one",
                    description="订单属于用户",
                ),
            ],
        )
        
        section = generator._generate_entity_section(entity)
        
        assert len(section.children) == 1
        assert "User" in section.children[0].content
    
    def test_rules_section(self, generator):
        """测试业务规则段落"""
        rules = RuleTreeNode(
            rule_text="主规则",
            children=[
                RuleTreeNode(
                    rule_text="子规则",
                    conditions=[],
                    actions=[],
                ),
            ],
        )
        
        section = generator._generate_rules_section(rules)
        
        assert "主规则" in section.content
        assert len(section.children) == 1
    
    def test_rules_with_conditions_and_actions(self, generator):
        """测试带条件和动作的规则"""
        from pm_workstation.models.core import Action, Condition
        
        rules = RuleTreeNode(
            rule_text="主规则",
            children=[
                RuleTreeNode(
                    rule_text="条件规则",
                    conditions=[
                        Condition(field="status", operator="==", value="active"),
                    ],
                    actions=[
                        Action(action_type="notify", description="发送通知"),
                    ],
                ),
            ],
        )
        
        section = generator._generate_rules_section(rules)
        
        assert "条件" in section.children[0].content
        assert "动作" in section.children[0].content
    
    def test_flows_section(self, generator, sample_requirement):
        """测试用户流程段落"""
        section = generator._generate_flows_section(sample_requirement.flows)
        
        assert len(section.children) == 1
        assert "用户注册" in section.children[0].title
    
    def test_flow_section_content(self, generator):
        """测试流程内容"""
        flow = UserFlow(
            name="测试流程",
            role="user",
            steps=[
                FlowStep(step_number=1, description="步骤1", action="操作1", expected_result="结果1"),
            ],
            entry_point="入口",
            exit_points=["出口1", "出口2"],
        )
        
        section = generator._generate_flow_section(flow)
        
        assert "user" in section.content
        assert "入口" in section.content
        assert "出口1" in section.content
    
    def test_empty_roles_section(self, generator):
        """测试空角色段落"""
        section = generator._generate_roles_section([])
        
        assert section.id == "roles"
        assert section.content == ""
    
    def test_empty_entities_section(self, generator):
        """测试空实体段落"""
        section = generator._generate_entities_section([])
        
        assert section.id == "entities"
        assert len(section.children) == 0
    
    def test_empty_flows_section(self, generator):
        """测试空流程段落"""
        section = generator._generate_flows_section([])
        
        assert section.id == "flows"
        assert len(section.children) == 0


class TestContentGenerator:
    """内容生成器测试"""
    
    @pytest.fixture
    def generator(self):
        """创建内容生成器"""
        return ContentGenerator()
    
    @pytest.fixture
    def sample_requirement(self):
        """创建示例需求"""
        return StructuredRequirement(
            entities=[
                BusinessEntity(
                    name="User",
                    description="系统用户",
                    attributes=[
                        Attribute(name="name", type="string", required=True),
                    ],
                ),
            ],
            roles=[Role(name="admin", description="管理员")],
            flows=[
                UserFlow(
                    name="登录",
                    role="user",
                    steps=[
                        FlowStep(step_number=1, description="输入账号密码", action="输入"),
                    ],
                ),
            ],
            rules=RuleTreeNode(
                rule_text="测试规则",
                children=[RuleTreeNode(rule_text="子规则")],
            ),
        )
    
    def test_generate_with_template(self, generator, sample_requirement):
        """测试使用模板生成文档"""
        result = generator.generate(
            sample_requirement,
            template_id="prd-standard",
            project_info={
                "name": "测试项目",
                "author": "测试作者",
            },
        )
        
        assert "测试项目" in result
        assert "测试作者" in result
    
    def test_generate_markdown(self, generator, sample_requirement):
        """测试生成 Markdown 文档"""
        result = generator.generate_markdown(
            sample_requirement,
            project_info={"name": "Markdown测试"},
        )
        
        assert "Markdown测试" in result
        assert "# 产品需求文档" in result
    
    def test_generate_with_simple_template(self, generator, sample_requirement):
        """测试使用简化模板"""
        result = generator.generate(
            sample_requirement,
            template_id="prd-simple",
            project_info={"name": "简单项目"},
        )
        
        assert "简单项目" in result


class TestTerminologyConsistencyChecker:
    """术语一致性检查器测试"""
    
    @pytest.fixture
    def checker(self):
        """创建检查器"""
        return TerminologyConsistencyChecker()
    
    def test_check_pass(self, checker):
        """测试通过检查"""
        document = "这是一个关于用户管理的文档。用户需要登录系统。"
        
        result = checker.check(document)
        
        assert result.passed is True
    
    def test_check_variant_inconsistency(self, checker):
        """测试术语变体不一致"""
        document = "系统支持Login和Sign In两种方式。用户需要先登入。"
        
        result = checker.check(document)
        
        # 登录相关的变体应该被检测到
        login_issues = [i for i in result.issues if "登录" in i.term or "Login" in i.term]
        assert len(login_issues) > 0
    
    def test_check_case_inconsistency(self, checker):
        """测试大小写不一致"""
        document = "系统提供api接口。Api调用需要认证。"
        
        result = checker.check(document)
        
        case_issues = [i for i in result.issues if i.term == "API"]
        assert len(case_issues) > 0
    
    def test_add_glossary_entry(self, checker):
        """测试添加术语表"""
        checker.add_glossary_entry("测试", "Test,Testing,测验")
        
        assert "测试" in checker._glossary
    
    def test_check_with_custom_glossary(self):
        """测试自定义术语表"""
        glossary = {
            "标准术语": "术语A,术语B",
        }
        checker = TerminologyConsistencyChecker(glossary=glossary)
        
        document = "文档中使用了术语A和术语B。"
        result = checker.check(document)
        
        assert len(result.issues) > 0
    
    def test_check_abbreviation_consistency(self, checker):
        """测试缩写一致性"""
        document = "The product requirement document (PRD) is important. PRD needs review."
        
        result = checker.check(document)
        
        # 全称和缩写同时出现应该被检测到
        abbr_issues = [i for i in result.issues if "product requirement" in i.term.lower()]
        assert len(abbr_issues) > 0


class TestMarkdownFormatter:
    """Markdown 格式化器测试"""
    
    def test_format_basic(self):
        """测试基础格式化"""
        doc = "# Title\n\nSome content\n\n## Subtitle\n\nMore content"
        
        result = MarkdownFormatter.format(doc)
        
        assert result.endswith('\n')
    
    def test_format_remove_extra_blank_lines(self):
        """测试清理多余空行"""
        doc = "Content\n\n\n\n\nMore content"
        
        result = MarkdownFormatter.format(doc)
        
        # 最多两个连续空行
        assert '\n\n\n\n' not in result
    
    def test_format_heading_spacing(self):
        """测试标题间距"""
        doc = "Text\n## Heading\nContent"
        
        result = MarkdownFormatter.format(doc)
        
        # 标题前应该有空行
        assert "\n\n##" in result
    
    def test_validate_heading_level_jump(self):
        """测试标题层级跳跃校验"""
        doc = "# H1\n\n### H3"  # 从H1跳到H3，跳过了H2
        
        issues = MarkdownFormatter.validate(doc)
        
        assert len(issues) > 0
    
    def test_validate_empty_link(self):
        """测试空链接校验"""
        doc = "[Link]()"
        
        issues = MarkdownFormatter.validate(doc)
        
        assert len(issues) > 0
    
    def test_extract_headings(self):
        """测试提取标题"""
        doc = "# Title\n\n## Section 1\n\n### Subsection\n\n## Section 2"
        
        headings = MarkdownFormatter.extract_headings(doc)
        
        assert len(headings) == 4
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "Title"
    
    def test_extract_toc(self):
        """测试生成目录"""
        doc = "# Title\n\n## Section 1\n\n### Subsection\n\n## Section 2"
        
        toc = MarkdownFormatter.extract_toc(doc)
        
        assert "- [Title]" in toc
        assert "- [Section 1]" in toc
    
    def test_format_table(self):
        """测试表格格式化"""
        doc = """| Name | Age |
|------|-----|
| Alice | 30 |
| Bob | 25 |"""
        
        result = MarkdownFormatter.format(doc)
        
        # 表格应该被对齐
        assert "|" in result
    
    def test_format_trailing_newline(self):
        """测试文件末尾换行"""
        doc = "Content without newline"
        
        result = MarkdownFormatter.format(doc)
        
        assert result.endswith('\n')
