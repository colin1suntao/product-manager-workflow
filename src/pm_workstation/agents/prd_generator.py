"""PRD 文档生成 Agent

根据结构化需求生成产品需求文档 (PRD)。
"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.model_router.fallback_handler import FallbackHandler
from pm_workstation.skills.loader import SkillLoader


class PRDGenerator:
    """PRD 文档生成器 - 将需求转化为标准化的产品需求文档"""

    def __init__(self, llm_handler: LLMBackend | FallbackHandler):
        """初始化 PRD 生成器

        Args:
            llm_handler: LLM 处理器
        """
        self.llm_handler = llm_handler
        self.skill_loader = SkillLoader()

    async def generate(
        self,
        requirement_text: str,
        structured_requirement=None,
        skills: list[str] | None = None,
    ) -> str:
        """生成 PRD 文档

        Args:
            requirement_text: 原始需求文本
            structured_requirement: 结构化需求（可选）
            skills: PM Skills 技能名称列表（可选）

        Returns:
            Markdown 格式的 PRD 文档
        """
        prompt = self._build_prompt(requirement_text, structured_requirement, skills)

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._extract_markdown(response.content)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个资深产品经理，擅长撰写清晰、完整、可执行的产品需求文档 (PRD)。

你的任务是：根据产品需求描述，生成一份标准化的 PRD 文档。

## 文档结构要求

PRD 文档必须包含以下章节：

### 1. 产品概述
- 产品名称和定位
- 解决的问题和目标用户
- 产品愿景和核心价值

### 2. 目标用户
- 用户画像（角色、特征、痛点）
- 使用场景

### 3. 功能需求
- 功能模块清单（按优先级排列）
- 每个功能的详细描述
  - 功能说明
  - 用户故事
  - 验收标准
  - 优先级（P0/P1/P2）

### 4. 信息架构
- 页面结构图（用文字描述层级关系）
- 核心页面的字段和交互说明

### 5. 用户流程
- 关键任务的完整用户流程
- 正常流程和异常流程

### 6. 非功能需求
- 性能要求（响应时间、并发数等）
- 安全要求（认证、授权、数据加密等）
- 可用性要求（SLA、容灾等）
- 兼容性要求（浏览器、设备、OS）

### 7. 数据模型
- 核心业务实体及属性
- 实体间的关系

### 8. 迭代计划
- MVP 版本范围
- 后续迭代规划
- 里程碑和时间线

## 写作要求

- 使用 Markdown 格式
- 语言简洁、准确、无歧义
- 每个功能都要有明确的验收标准
- 使用表格、列表等结构化表达
- 优先级标注清晰（P0=最高，P1=重要，P2=一般）

**重要：只输出 PRD 文档内容本身，用 ```markdown 代码块包裹，不要输出任何解释文字。**"""

    def _build_prompt(self, requirement_text: str, structured_requirement=None, skills: list[str] | None = None) -> str:
        """构建生成提示词"""
        parts = [f"""请根据以下产品需求，生成一份完整的产品需求文档 (PRD)：

## 需求描述

{requirement_text}
"""]

        # 添加 PM Skills 指导
        if skills:
            loaded_skills = self.skill_loader.load_multiple(skills)
            if loaded_skills:
                parts.append("""
## 应用的 PM Skills

请在生成 PRD 时，参考以下产品经理技能的方法论和框架：
""")
                for skill in loaded_skills:
                    parts.append(f"### {skill.name}")
                    if skill.description:
                        parts.append(f"**描述**: {skill.description}")
                    if skill.system_prompt:
                        parts.append(f"\n{skill.system_prompt}")
                    elif skill.get_full_prompt():
                        parts.append(f"\n{skill.get_full_prompt()}")
                    parts.append("")

        if structured_requirement:
            parts.append("""## 结构化需求分析

### 业务实体
""")
            for entity in structured_requirement.entities:
                parts.append(f"- **{entity.name}**: {entity.description}")
                if entity.attributes:
                    for attr in entity.attributes:
                        parts.append(f"  - 属性: {attr}")
                if hasattr(entity, 'relations') and entity.relations:
                    for rel in entity.relations:
                        parts.append(f"  - 关联: {rel}")

            if structured_requirement.roles:
                parts.append("\n### 用户角色\n")
                for role in structured_requirement.roles:
                    perms = ", ".join(role.permissions) if hasattr(role, 'permissions') and role.permissions else "待定义"
                    parts.append(f"- **{role.name}**: {role.description} (权限: {perms})")

            if structured_requirement.flows:
                parts.append("\n### 用户操作流程\n")
                for flow in structured_requirement.flows:
                    parts.append(f"- **{flow.name}** (角色: {flow.role_name if hasattr(flow, 'role_name') else '未指定'})")
                    for i, step in enumerate(flow.steps, 1):
                        parts.append(f"  {i}. {step}")

            if structured_requirement.edge_cases:
                parts.append("\n### 边界场景\n")
                for ec in structured_requirement.edge_cases:
                    parts.append(f"- **{ec.description}**: 预期行为: {ec.expected_behavior if hasattr(ec, 'expected_behavior') else '待定义'}")

            if structured_requirement.clarifications:
                parts.append("\n### 待澄清问题\n")
                for q in structured_requirement.clarifications:
                    parts.append(f"- {q.question}")

        parts.append("""
请开始撰写 PRD 文档，确保：
1. 文档结构完整，覆盖上述所有章节
2. 功能描述详细到可以直接指导开发
3. 验收标准具体、可测试
4. 优先级标注合理
5. 使用专业的产品术语
6. 如果提供了 PM Skills，请将相关框架和方法论自然融入文档中""")

        return "\n".join(parts)

    def _extract_markdown(self, content: str) -> str:
        """从 LLM 响应中提取 Markdown 内容"""
        content = content.strip()

        # 尝试提取 ```markdown 代码块
        if "```markdown" in content:
            start = content.index("```markdown") + 11
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
            return content[start:].strip()

        # 尝试提取 ``` 代码块
        if "```" in content:
            start = content.index("```") + 3
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
            return content[start:].strip()

        # 如果已经是 Markdown 格式（包含标题）
        if "# " in content or "## " in content:
            return content

        # 兜底：返回原始内容
        return content
