"""PRD文档内容生成器

将结构化需求转换为PRD文档内容，并使用模板引擎生成最终文档。
"""

from datetime import datetime
from typing import Optional

from pm_workstation.document.structure_generator import DocumentSection, DocumentStructureGenerator
from pm_workstation.document.template_engine import TemplateEngine
from pm_workstation.document.terminology_checker import TerminologyConsistencyChecker
from pm_workstation.models.core import StructuredRequirement


class ContentGenerator:
    """PRD内容生成器
    
    将结构化需求转换为完整的 PRD 文档。
    """
    
    def __init__(
        self,
        template_engine: Optional[TemplateEngine] = None,
        structure_generator: Optional[DocumentStructureGenerator] = None,
    ):
        self._template_engine = template_engine or TemplateEngine()
        self._structure_generator = structure_generator or DocumentStructureGenerator()
    
    def generate(
        self,
        requirement: StructuredRequirement,
        template_id: str = "prd-standard",
        project_info: Optional[dict] = None,
    ) -> str:
        """生成 PRD 文档
        
        Args:
            requirement: 结构化需求
            template_id: 模板ID
            project_info: 项目信息（名称、作者等）
            
        Returns:
            渲染后的 PRD 文档
        """
        project_info = project_info or {}
        
        # 生成文档结构
        sections = self._structure_generator.generate(requirement)
        
        # 构建渲染上下文
        context = self._build_context(requirement, sections, project_info)
        
        # 渲染模板
        return self._template_engine.render(template_id, context)
    
    def generate_markdown(
        self,
        requirement: StructuredRequirement,
        project_info: Optional[dict] = None,
    ) -> str:
        """生成 Markdown 格式 PRD（不使用模板）
        
        Args:
            requirement: 结构化需求
            project_info: 项目信息
            
        Returns:
            Markdown 文档
        """
        sections = self._structure_generator.generate(requirement)
        return self._sections_to_markdown(sections, project_info)
    
    def _build_context(
        self,
        requirement: StructuredRequirement,
        sections: list[DocumentSection],
        project_info: dict,
    ) -> dict:
        """构建模板渲染上下文"""
        context = {
            # 项目信息
            "project_name": project_info.get("name", "未命名项目"),
            "doc_version": project_info.get("version", "1.0"),
            "created_date": project_info.get("date", datetime.now().strftime("%Y-%m-%d")),
            "author": project_info.get("author", "PM Workstation"),
            
            # 概述
            "project_background": project_info.get("background", ""),
            "project_goals": project_info.get("goals", ""),
            "project_scope": project_info.get("scope", ""),
            
            # 布尔标志
            "has_roles": len(requirement.roles) > 0,
            "has_entities": len(requirement.entities) > 0,
            "has_rules": len(requirement.rules.children) > 0 if requirement.rules else False,
            "has_flows": len(requirement.flows) > 0,
            
            # 文档段落内容
            "roles_table": self._find_section_content(sections, "roles"),
            "entities_content": self._find_section_content(sections, "entities"),
            "functional_requirements": self._generate_functional_requirements(requirement),
            "business_rules": self._find_section_content(sections, "rules"),
            "user_flows_content": self._find_section_content(sections, "flows"),
            
            # 非功能需求
            "performance_requirements": project_info.get("performance_requirements", ""),
            "security_requirements": project_info.get("security_requirements", ""),
            "compatibility_requirements": project_info.get("compatibility_requirements", ""),
            
            # 附录
            "appendix_content": project_info.get("appendix", ""),
        }
        
        return context
    
    def _find_section_content(
        self,
        sections: list[DocumentSection],
        section_id: str,
    ) -> str:
        """查找指定段落的内容"""
        for section in sections:
            if section.id == section_id:
                return self._section_to_markdown(section)
        return ""
    
    def _section_to_markdown(self, section: DocumentSection, indent: int = 0) -> str:
        """将文档段落转换为 Markdown"""
        heading_prefix = "#" * section.level
        parts = [f"{heading_prefix} {section.title}"]
        
        if section.content:
            parts.append(section.content)
        
        for child in section.children:
            parts.append(self._section_to_markdown(child, indent + 1))
        
        return "\n\n".join(parts)
    
    def _sections_to_markdown(
        self,
        sections: list[DocumentSection],
        project_info: Optional[dict] = None,
    ) -> str:
        """将段落列表转换为完整 Markdown 文档"""
        project_info = project_info or {}
        
        # 文档头部
        header = f"""# 产品需求文档

| 属性 | 值 |
|------|-----|
| 项目名称 | {project_info.get('name', '未命名项目')} |
| 文档版本 | {project_info.get('version', '1.0')} |
| 创建日期 | {project_info.get('date', datetime.now().strftime('%Y-%m-%d'))} |
| 作者 | {project_info.get('author', 'PM Workstation')} |

"""
        
        # 概述
        overview = f"""## 概述

### 背景

{project_info.get('background', '')}

### 目标

{project_info.get('goals', '')}

### 范围

{project_info.get('scope', '')}
"""
        
        body_parts = []
        for section in sections:
            body_parts.append(self._section_to_markdown(section))
        
        return header + overview + "\n\n".join(body_parts)
    
    def _generate_functional_requirements(self, requirement: StructuredRequirement) -> str:
        """生成功能需求内容"""
        parts = []
        
        # 从实体生成功能需求
        for entity in requirement.entities:
            parts.append(f"### {entity.name}管理")
            parts.append(f"- 支持{entity.name}的创建、编辑、删除和查询操作")
            
            required_attrs = [a for a in entity.attributes if a.required]
            if required_attrs:
                attr_names = ", ".join(a.name for a in required_attrs)
                parts.append(f"- 必填字段：{attr_names}")
        
        # 从角色生成权限需求
        for role in requirement.roles:
            parts.append(f"### {role.name}权限")
            parts.append(f"- {role.description}")
        
        return "\n\n".join(parts)
