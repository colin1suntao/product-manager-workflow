import logging
from datetime import datetime

from pm_workstation.component_library.models import ComponentTemplate

logger = logging.getLogger(__name__)


class ComponentTemplateStore:
    def __init__(self) -> None:
        self._templates: dict[str, ComponentTemplate] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        defaults = [
            ComponentTemplate(
                id="comp-proto-1",
                name="标准网页原型",
                description="适用于标准 Web 应用的原型模板，包含导航栏、内容区、页脚等基础布局",
                content="""你是一个专业的原型设计师。请根据需求生成高保真原型 HTML。

## 设计规范
- 使用现代化 UI 风格，参考 Ant Design / shadcn/ui 设计语言
- 页面结构：顶部导航栏 → 内容区域 → 页脚
- 响应式设计，支持移动端和桌面端
- 使用柔和的色彩方案，主色 #3B82F6
- 字体使用系统默认字体栈

## 必须包含的组件
1. 顶部导航栏：Logo、导航链接、用户头像
2. 内容区域：根据需求展示核心功能
3. 页脚：版权信息、链接

## 技术要求
- 使用 HTML + Tailwind CSS (CDN)
- 所有交互使用原生 JavaScript
- 页面需包含基本的交互动效（hover、点击反馈等）""",
                tags=["网页", "标准", "通用"],
            ),
            ComponentTemplate(
                id="comp-proto-2",
                name="移动端原型",
                description="适用于移动端 App 或 H5 页面的原型模板",
                content="""你是一个专业的移动端原型设计师。请根据需求生成移动端原型 HTML。

## 设计规范
- 移动优先设计，宽度 375px 基准
- 使用 Material Design 设计语言
- 底部 Tab 导航栏
- 手势交互：滑动、点击、长按

## 必须包含的组件
1. 顶部状态栏 + 标题栏
2. 底部 Tab 导航（首页、功能、我的）
3. 卡片式内容布局
4. 浮动操作按钮 (FAB)

## 技术要求
- 使用 HTML + Tailwind CSS (CDN)
- 模拟移动端视口
- 触摸事件支持""",
                tags=["移动端", "App", "H5"],
            ),
        ]
        for t in defaults:
            self._templates[t.id] = t

    async def list_all(self) -> list[ComponentTemplate]:
        return list(self._templates.values())

    async def get(self, template_id: str) -> ComponentTemplate | None:
        return self._templates.get(template_id)

    async def create(self, template: ComponentTemplate) -> ComponentTemplate:
        self._templates[template.id] = template
        return template

    async def update(self, template_id: str, updates: dict) -> ComponentTemplate | None:
        template = self._templates.get(template_id)
        if not template:
            return None
        for key, value in updates.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        template.updated_at = datetime.now()
        return template

    async def delete(self, template_id: str) -> bool:
        return self._templates.pop(template_id, None) is not None
