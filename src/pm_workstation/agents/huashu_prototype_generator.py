"""Huashu Design 原型生成 Agent

基于 huashu-design 理念的高保真原型生成器。
使用 React + Babel 技术栈，遵循 huashu-design 的设计哲学和技术规范。
"""

from pm_workstation.model_router.base import LLMBackend, LLMMessage, LLMResponse
from pm_workstation.model_router.fallback_handler import FallbackHandler


# huashu-design 的核心技术规范
HUASHU_REACT_SETUP = """## 技术架构（必须遵守）

### React + Babel 配置
在 HTML 的 `<head>` 中必须包含以下固定版本的 script 标签：
```html
<script src="https://unpkg.com/react@18.3.1/umd/react.development.js" integrity="sha384-hD6/rw4ppMLGNu3tX5cjIb+uRZ7UkRJ6BPkLpg4hAu/6onKUg4lLsHAs9EBPT82L" crossorigin="anonymous"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js" integrity="sha384-u6aeetuaXnQ38mYT8rp6sbXaQe3NL9t+IBXmnYxwkUI2Hw4bsp2Wvmx4yRQF1uAm" crossorigin="anonymous"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" integrity="sha384-m08KidiNqLdpJqLq95G/LEi8Qvjl/xUYll3QILypMoQ65QorJ9Lvtp2RXYGBFj1y" crossorigin="anonymous"></script>
```

### 三条不可违反的规则
1. **styles 对象必须唯一命名**：禁止使用 `const styles = {...}`，必须用唯一前缀如 `const homeStyles = {...}`
2. **Scope 不共享**：每个 `<script type="text/babel">` 之间 scope 不通，必须用 `Object.assign(window, {ComponentName})` 导出组件
3. **禁止使用 scrollIntoView**：会搞坏容器滚动，使用 `container.scrollTop = target.offsetTop` 替代

### 文件结构
默认使用单文件架构（所有 JSX inline 写在 `<script type="text/babel">` 中），除非：
- 单文件 >1000 行难维护 → 拆成外部文件并用 HTTP server
- 需要多 agent 并行 → 每屏独立 HTML + iframe 聚合"""


HUASHU_DESIGN_PRINCIPLES = """## 设计原则（huashu-design 理念）

### 核心哲学
1. **从 existing context 出发**：不要凭空设计，先理解需求和品牌上下文
2. **反 AI slop**：避免紫色渐变、emoji 图标、圆角卡片+左 border accent、SVG 画人脸等 AI 默认模式
3. **诚实的 placeholder**：没数据就写注释，不要编造假数据；没图标就留灰色方块+文字标签
4. **系统优先，不要填充**：每个元素都必须 earn its place，空白是设计问题，用构图解决

### 正向设计指南
- 使用 `text-wrap: pretty` + CSS Grid + 高级 CSS 排版细节
- 使用 oklch() 或品牌色，不凭空发明新颜色
- 一个细节做到 120%，其他做到 80%（品味 = 在合适的地方足够精致）
- 使用有特点的 display + body 字体配对，避免 Inter/Roboto/Arial
- 中文排印使用「」引号，不是 ""

### 信息密度分型
- **克制型（默认）**：少一层容器、少一个 border、少一个装饰性 icon，给内容留气口
- **高密度型（AI/数据类产品）**：每屏至少 3 处可见的产品差异化信息（非装饰性数据、状态推断、上下文关联）"""


class HuashuPrototypeGenerator:
    """基于 huashu-design 理念的原型生成器
    
    生成高保真、可交互的 React + Babel HTML 原型，
    遵循 huashu-design 的设计哲学和技术规范。
    """

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
            structured_requirement: 结构化需求（可选）

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
        return f"""你是一位用 HTML 工作的资深设计师和前端工程师，不是程序员。
你精通 huashu-design 设计哲学，擅长用 React + Babel 构建高保真、可交互的原型。

**你的媒介是 HTML，但你的产出形式会变**：
- 做 App 原型时，像 UX 设计师一样思考（用 ios_frame.jsx 设备框、真图、可点击流程）
- 做 Dashboard 时，像数据可视化设计师一样思考（精确布局、数据驱动）
- 做展示页时，像幻灯片设计师一样思考（1920×1080、演讲节奏）

{HUASHU_DESIGN_PRINCIPLES}

{HUASHU_REACT_SETUP}

## 交互要求
- 按钮点击有反馈效果（hover、active 状态）
- 表单有输入验证和提交动画
- 导航可以切换不同视图/页面（用 React state 管理）
- 使用 localStorage 模拟数据持久化（如果需要）
- App 原型必须可点击、可交互，不是静态摆拍

## 内容要求
- 填充真实的模拟数据（不要用"Lorem ipsum"）
- 页面标题和模块标题要贴合用户需求
- 功能模块要完整，不要只写占位符
- App 原型默认去取真实图片（Wikimedia Commons、Unsplash、Met Museum）

## 输出格式
**重要：只输出 HTML 代码本身，用 ```html 代码块包裹，不要输出任何解释文字。**
HTML 必须是完整的、自包含的，双击即可在浏览器中打开。"""

    def _build_prompt(self, requirement_text: str, structured_requirement=None) -> str:
        """构建生成提示词"""
        parts = [f"""请根据以下产品需求，生成一个高保真、可交互的 HTML 原型：

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
## 生成要求

1. **先思考再动手**：在 HTML 开头用注释写下你的 assumptions + reasoning + placeholders
2. **覆盖所有核心功能**：确保需求中提到的每个功能模块都有对应的界面
3. **真实交互**：使用 React state 管理页面切换、模态框、表单等交互
4. **专业设计**：遵循 huashu-design 反 AI slop 原则，避免视觉最大公约数
5. **完整代码**：输出完整的 HTML 文档，包含 React + Babel 配置

请开始生成 HTML 原型。""")

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
