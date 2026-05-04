"""PRD文档模板引擎

管理PRD文档模板，支持变量替换和条件渲染。
"""

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplateVariable(BaseModel):
    """模板变量定义"""
    name: str = Field(..., description="变量名称")
    description: str = Field(default="", description="变量描述")
    default: str = Field(default="", description="默认值")
    required: bool = Field(default=False, description="是否必需")


class TemplateSection(BaseModel):
    """模板段落"""
    id: str = Field(..., description="段落唯一标识")
    title: str = Field(..., description="段落标题")
    level: int = Field(default=2, description="标题级别 (1=H1, 2=H2, ...)")
    content_template: str = Field(..., description="内容模板（支持变量占位符）")
    variables: list[TemplateVariable] = Field(default_factory=list, description="使用的变量")
    condition: Optional[str] = Field(default=None, description="渲染条件")
    children: list["TemplateSection"] = Field(default_factory=list, description="子段落")


class PRDTemplate(BaseModel):
    """PRD文档模板"""
    id: str = Field(..., description="模板唯一标识")
    name: str = Field(..., description="模板名称")
    description: str = Field(default="", description="模板描述")
    version: str = Field(default="1.0.0", description="模板版本")
    sections: list[TemplateSection] = Field(default_factory=list, description="模板段落")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class TemplateEngine:
    """PRD模板引擎
    
    负责加载模板、渲染变量、条件渲染和生成最终文档。
    """
    
    def __init__(self):
        self._templates: dict[str, PRDTemplate] = {}
        self._register_default_templates()
    
    def register_template(self, template: PRDTemplate):
        """注册模板
        
        Args:
            template: PRD模板
        """
        self._templates[template.id] = template
    
    def get_template(self, template_id: str) -> Optional[PRDTemplate]:
        """获取模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            PRD模板，不存在时返回None
        """
        return self._templates.get(template_id)
    
    def list_templates(self) -> list[PRDTemplate]:
        """列出所有模板
        
        Returns:
            模板列表
        """
        return list(self._templates.values())
    
    def render(
        self,
        template_id: str,
        context: dict[str, Any],
    ) -> str:
        """渲染模板
        
        Args:
            template_id: 模板ID
            context: 渲染上下文（变量值映射）
            
        Returns:
            渲染后的文档字符串
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        sections_content = []
        for section in template.sections:
            rendered = self._render_section(section, context)
            if rendered:
                sections_content.append(rendered)
        
        return "\n\n".join(sections_content)
    
    def render_section(
        self,
        section: TemplateSection,
        context: dict[str, Any],
    ) -> Optional[str]:
        """渲染单个段落
        
        Args:
            section: 模板段落
            context: 渲染上下文
            
        Returns:
            渲染后的段落内容，条件不满足时返回None
        """
        return self._render_section(section, context)
    
    def get_required_variables(self, template_id: str) -> list[TemplateVariable]:
        """获取模板所需的变量列表
        
        Args:
            template_id: 模板ID
            
        Returns:
            必需变量列表
        """
        template = self.get_template(template_id)
        if not template:
            return []
        
        variables = []
        self._collect_variables(template.sections, variables)
        return variables
    
    def _render_section(
        self,
        section: TemplateSection,
        context: dict[str, Any],
    ) -> Optional[str]:
        """递归渲染段落"""
        # 检查条件
        if section.condition and not self._evaluate_condition(section.condition, context):
            return None
        
        # 生成标题
        heading_prefix = "#" * section.level
        title = self._substitute_variables(section.title, context)
        
        # 渲染内容
        content = self._substitute_variables(section.content_template, context)
        
        # 渲染子段落
        children_content = []
        for child in section.children:
            rendered_child = self._render_section(child, context)
            if rendered_child:
                children_content.append(rendered_child)
        
        # 组合段落
        parts = [f"{heading_prefix} {title}"]
        if content.strip():
            parts.append(content)
        parts.extend(children_content)
        
        return "\n\n".join(parts)
    
    def _substitute_variables(self, text: str, context: dict[str, Any]) -> str:
        """替换模板变量
        
        支持格式: {{variable_name}} 和 {{variable_name|default_value}}
        """
        def replace_var(match):
            var_expr = match.group(1).strip()
            parts = var_expr.split("|", 1)
            var_name = parts[0].strip()
            default = parts[1].strip() if len(parts) > 1 else ""
            
            value = context.get(var_name, "")
            if not value and default:
                value = default
            return str(value)
        
        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)
    
    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """评估渲染条件
        
        支持简单条件: "has_entities", "has_flows", "entity_count > 0"
        """
        condition = condition.strip()
        
        # 布尔变量检查: has_xxx -> check context.get("has_xxx")
        if condition.startswith("has_"):
            # 先尝试直接查找
            value = context.get(condition)
            if value is not None:
                return bool(value)
            # 再尝试去掉 has_ 前缀
            var_name = condition[4:]
            return bool(context.get(var_name))
        
        # 比较表达式
        match = re.match(r'(\w+)\s*([><=!]+)\s*(\w+)', condition)
        if match:
            var_name, operator, value_str = match.groups()
            var_value = context.get(var_name, 0)
            
            try:
                value = int(value_str)
            except ValueError:
                value = value_str
            
            if operator == ">":
                return var_value > value
            elif operator == ">=":
                return var_value >= value
            elif operator == "<":
                return var_value < value
            elif operator == "<=":
                return var_value <= value
            elif operator == "==" or operator == "=":
                return var_value == value
            elif operator == "!=":
                return var_value != value
        
        return True
    
    def _collect_variables(
        self,
        sections: list[TemplateSection],
        variables: list[TemplateVariable],
    ):
        """递归收集所有变量"""
        seen = set()
        for section in sections:
            for var in section.variables:
                if var.name not in seen:
                    seen.add(var.name)
                    variables.append(var)
            self._collect_variables(section.children, variables)
    
    def _register_default_templates(self):
        """注册默认PRD模板"""
        prd_template = PRDTemplate(
            id="prd-standard",
            name="标准PRD模板",
            description="标准产品需求文档模板，适用于大多数软件项目",
            version="1.0.0",
            sections=[
                TemplateSection(
                    id="doc-header",
                    title="产品需求文档",
                    level=1,
                    content_template="| 属性 | 值 |\n|------|-----|\n| 项目名称 | {{project_name}} |\n| 文档版本 | {{doc_version|1.0}} |\n| 创建日期 | {{created_date}} |\n| 作者 | {{author}} |",
                    variables=[
                        TemplateVariable(name="project_name", description="项目名称", required=True),
                        TemplateVariable(name="doc_version", description="文档版本", default="1.0"),
                        TemplateVariable(name="created_date", description="创建日期", required=True),
                        TemplateVariable(name="author", description="作者", required=True),
                    ],
                ),
                TemplateSection(
                    id="overview",
                    title="概述",
                    level=2,
                    content_template="## 背景\n\n{{project_background}}\n\n## 目标\n\n{{project_goals}}\n\n## 范围\n\n{{project_scope}}",
                    variables=[
                        TemplateVariable(name="project_background", description="项目背景", required=True),
                        TemplateVariable(name="project_goals", description="项目目标", required=True),
                        TemplateVariable(name="project_scope", description="项目范围", required=True),
                    ],
                ),
                TemplateSection(
                    id="roles",
                    title="用户角色",
                    level=2,
                    content_template="{{roles_table}}",
                    condition="has_roles",
                    variables=[
                        TemplateVariable(name="roles_table", description="用户角色表格", required=True),
                    ],
                ),
                TemplateSection(
                    id="entities",
                    title="业务实体",
                    level=2,
                    content_template="{{entities_content}}",
                    condition="has_entities",
                    variables=[
                        TemplateVariable(name="entities_content", description="业务实体内容", required=True),
                    ],
                ),
                TemplateSection(
                    id="functional-requirements",
                    title="功能需求",
                    level=2,
                    content_template="{{functional_requirements}}",
                    variables=[
                        TemplateVariable(name="functional_requirements", description="功能需求列表", required=True),
                    ],
                    children=[
                        TemplateSection(
                            id="business-rules",
                            title="业务规则",
                            level=3,
                            content_template="{{business_rules}}",
                            condition="has_rules",
                            variables=[
                                TemplateVariable(name="business_rules", description="业务规则内容", required=True),
                            ],
                        ),
                    ],
                ),
                TemplateSection(
                    id="user-flows",
                    title="用户流程",
                    level=2,
                    content_template="{{user_flows_content}}",
                    condition="has_flows",
                    variables=[
                        TemplateVariable(name="user_flows_content", description="用户流程内容", required=True),
                    ],
                ),
                TemplateSection(
                    id="non-functional",
                    title="非功能需求",
                    level=2,
                    content_template="## 性能要求\n\n{{performance_requirements}}\n\n## 安全要求\n\n{{security_requirements}}\n\n## 兼容性要求\n\n{{compatibility_requirements}}",
                    variables=[
                        TemplateVariable(name="performance_requirements", description="性能要求"),
                        TemplateVariable(name="security_requirements", description="安全要求"),
                        TemplateVariable(name="compatibility_requirements", description="兼容性要求"),
                    ],
                ),
                TemplateSection(
                    id="appendix",
                    title="附录",
                    level=2,
                    content_template="{{appendix_content|}}",
                ),
            ],
        )
        
        self.register_template(prd_template)
        
        # 简化模板
        simple_template = PRDTemplate(
            id="prd-simple",
            name="简化PRD模板",
            description="简化的产品需求文档模板，适用于小型项目或敏捷开发",
            version="1.0.0",
            sections=[
                TemplateSection(
                    id="simple-header",
                    title="产品需求文档",
                    level=1,
                    content_template="| 属性 | 值 |\n|------|-----|\n| 项目名称 | {{project_name}} |\n| 日期 | {{created_date}} |",
                    variables=[
                        TemplateVariable(name="project_name", description="项目名称", required=True),
                        TemplateVariable(name="created_date", description="日期", required=True),
                    ],
                ),
                TemplateSection(
                    id="simple-requirements",
                    title="需求描述",
                    level=2,
                    content_template="{{requirements_text}}",
                    variables=[
                        TemplateVariable(name="requirements_text", description="需求描述", required=True),
                    ],
                ),
            ],
        )
        
        self.register_template(simple_template)
