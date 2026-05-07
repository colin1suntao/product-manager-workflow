"""原型生成 Agent

根据结构化需求生成可交互的 HTML 原型。
"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage
from pm_workstation.model_router.fallback_handler import FallbackHandler


class PrototypeGenerator:
    """原型生成器 - 将需求转化为可交互的 HTML 原型"""

    def __init__(self, llm_handler: LLMBackend | FallbackHandler):
        """初始化原型生成器

        Args:
            llm_handler: LLM 处理器
        """
        self.llm_handler = llm_handler

    async def generate(self, requirement_text: str, structured_requirement=None) -> str:
        """生成 HTML 原型

        Args:
            requirement_text: 原始需求文本
            structured_requirement: 结构化需求（可选，如果有解析结果则传入）

        Returns:
            完整的 HTML 原型字符串
        """
        prompt = self._build_prompt(requirement_text, structured_requirement)

        response = await self.llm_handler.chat([
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ])

        return self._extract_html(response.content)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个资深的前端工程师和交互设计师，擅长快速构建高保真、可交互的 HTML 原型。

你的任务是：根据产品需求，生成一个完整的、自包含的 HTML 原型页面。

## 输出要求

1. **完整的 HTML 文档**：包含 `<!DOCTYPE html>` 到 `</html>` 的完整文档
2. **内联样式**：所有 CSS 写在 `<style>` 标签内，不要引用外部文件
3. **内联脚本**：所有 JavaScript 写在 `<script>` 标签内，实现真实的交互效果
4. **响应式设计**：适配桌面和移动端
5. **现代 UI 风格**：使用现代化的设计语言（圆角、阴影、渐变、平滑过渡）

## 交互要求

- 按钮点击有反馈效果
- 表单有输入验证和提交动画
- 模态框/弹窗可以打开和关闭
- 导航可以切换不同视图/页面
- 表格支持排序、筛选、分页等常见操作
- 列表项支持增删改查操作
- 使用 localStorage 模拟数据持久化

## 设计原则

- 使用清晰的视觉层次（标题、正文、辅助文字）
- 颜色方案要协调，主色、辅色、背景色搭配合理
- 间距要舒适，留白充足
- 交互反馈要及时且明显（hover、active、loading 状态）
- 空状态要有引导提示

## 技术约束

- 不要使用任何外部 CDN 或框架（不用 React/Vue/jQuery/Tailwind）
- 使用原生 HTML5 + CSS3 + Vanilla JavaScript
- 可以使用 CSS Grid 和 Flexbox 进行布局
- 可以使用 CSS 变量管理颜色主题
- 所有代码必须在一个 HTML 文件中

## 内容要求

- 填充真实的模拟数据（不要用"Lorem ipsum"）
- 页面标题和模块标题要贴合用户需求
- 功能模块要完整，不要只写占位符

**重要：只输出 HTML 代码本身，用 ```html 代码块包裹，不要输出任何解释文字。**"""

    def _build_prompt(self, requirement_text: str, structured_requirement=None) -> str:
        """构建生成提示词"""
        parts = [f"""请根据以下产品需求，生成一个完整的、可交互的 HTML 原型页面：

## 需求描述

{requirement_text}
"""]

        if structured_requirement:
            parts.append("""## 结构化需求分析

### 业务实体
""")
            for entity in structured_requirement.entities:
                parts.append(f"- **{entity.name}**: {entity.description}")
                if entity.attributes:
                    for attr in entity.attributes:
                        parts.append(f"  - {attr}")

            if structured_requirement.roles:
                parts.append("\n### 用户角色\n")
                for role in structured_requirement.roles:
                    parts.append(f"- **{role.name}**: {role.description}")

            if structured_requirement.flows:
                parts.append("\n### 用户操作流程\n")
                for flow in structured_requirement.flows:
                    parts.append(f"- **{flow.name}**: {' → '.join(flow.steps[:5])}")

            if structured_requirement.edge_cases:
                parts.append("\n### 边界场景\n")
                for ec in structured_requirement.edge_cases:
                    parts.append(f"- {ec.description}")

        parts.append("""
请开始生成 HTML 原型，确保：
1. 覆盖需求中提到的所有核心功能模块
2. 每个功能都有可交互的界面元素
3. 使用真实的模拟数据填充
4. 包含页面导航，可以切换不同功能视图
5. 界面美观、专业、现代""")

        return "\n".join(parts)

    def _extract_html(self, content: str) -> str:
        """从 LLM 响应中提取 HTML 代码"""
        content = content.strip()

        # 尝试提取 ```html 代码块
        if "```html" in content:
            start = content.index("```html") + 7
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

        # 如果包含 <!DOCTYPE html>，直接返回
        if "<!DOCTYPE html>" in content or "<!doctype html>" in content:
            return content

        # 如果包含 <html>，包裹后返回
        if "<html" in content:
            return content

        # 兜底：返回原始内容
        return content
