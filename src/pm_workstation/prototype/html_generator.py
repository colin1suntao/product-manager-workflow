"""HTML/CSS/JS 代码生成器

将页面结构、组件匹配和交互配置生成为可交互的 HTML 原型。
"""

from typing import Optional

from pm_workstation.prototype.component_matcher import ComponentMatcher
from pm_workstation.prototype.interaction_configurator import InteractionConfigurator
from pm_workstation.prototype.page_structure import PageNode, PageStructure


class HTMLGenerator:
    """HTML 代码生成器
    
    将页面结构、组件匹配和交互配置生成为完整的 HTML/CSS/JS 原型代码。
    """
    
    def __init__(
        self,
        component_matcher: Optional[ComponentMatcher] = None,
        interaction_configurator: Optional[InteractionConfigurator] = None,
    ):
        self._component_matcher = component_matcher
        self._interaction_configurator = interaction_configurator or InteractionConfigurator()
    
    def generate(
        self,
        page_structure: PageStructure,
        include_css: bool = True,
        include_js: bool = True,
    ) -> dict[str, str]:
        """生成完整的原型代码
        
        Args:
            page_structure: 页面结构
            include_css: 是否包含CSS
            include_js: 是否包含JS
            
        Returns:
            包含 html、css、js 的字典
        """
        html_parts = []
        css_parts = []
        js_parts = []
        
        # 生成 HTML 头部
        html_parts.append(self._generate_head())
        html_parts.append("<body>")
        
        # 生成导航栏
        html_parts.append(self._generate_navigation(page_structure.navigation))
        
        # 生成页面内容
        html_parts.append('<main id="app-container">')
        for page in page_structure.pages[:10]:  # 限制页面数量
            html_parts.append(self._generate_page(page))
            
            if include_css:
                css_parts.append(self._generate_page_css(page))
            
            if include_js:
                js_parts.append(self._generate_page_js(page))
        html_parts.append("</main>")
        
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        html_content = "\n".join(html_parts)
        css_content = "\n\n".join(css_parts) if css_parts else self._generate_default_css()
        js_content = "\n\n".join(js_parts) if js_parts else self._generate_default_js()
        
        return {
            "html": html_content,
            "css": css_content,
            "js": js_content,
        }
    
    def generate_page(self, page: PageNode) -> str:
        """生成单个页面的 HTML
        
        Args:
            page: 页面节点
            
        Returns:
            HTML 字符串
        """
        return self._generate_page(page)
    
    def _generate_head(self) -> str:
        """生成 HTML 头部"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>原型预览</title>
    <style>
        :root {
            --primary-color: #1677ff;
            --success-color: #52c41a;
            --warning-color: #faad14;
            --error-color: #ff4d4f;
            --text-color: rgba(0, 0, 0, 0.88);
            --text-secondary: rgba(0, 0, 0, 0.65);
            --border-color: #d9d9d9;
            --bg-color: #ffffff;
            --bg-secondary: #f5f5f5;
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 16px;
            --spacing-lg: 24px;
            --spacing-xl: 32px;
            --border-radius: 6px;
            --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: var(--font-family); color: var(--text-color); background: var(--bg-secondary); }
    </style>
</head>"""
    
    def _generate_navigation(self, navigation: list[dict]) -> str:
        """生成导航栏"""
        if not navigation:
            return '<header id="app-header" style="background: var(--bg-color); border-bottom: 1px solid var(--border-color); padding: 12px 24px;"><nav><span style="font-size: 18px; font-weight: 600;">系统导航</span></nav></header>'
        
        nav_items = []
        for group in navigation[:5]:
            entity = group.get("entity", "Unknown")
            pages = group.get("pages", [])
            nav_items.append(f'<li style="position: relative; display: inline-block; margin-right: 16px;"><a href="#" style="text-decoration: none; color: var(--text-color); padding: 8px 12px; border-radius: 4px;" onmouseover="this.style.background=\'var(--bg-secondary)\'" onmouseout="this.style.background=\'transparent\'">{entity}</a></li>')
        
        return f"""<header id="app-header" style="background: var(--bg-color); border-bottom: 1px solid var(--border-color); padding: 12px 24px;">
    <nav>
        <span style="font-size: 18px; font-weight: 600; margin-right: 32px;">应用名称</span>
        <ul style="list-style: none; display: inline-flex;">
            {''.join(nav_items)}
        </ul>
    </nav>
</header>"""
    
    def _generate_page(self, page: PageNode) -> str:
        """生成页面 HTML"""
        layout = page.layout_hint or "card"
        
        content = self._generate_page_content(page, layout)
        
        return f"""<section id="{page.id}" style="background: var(--bg-color); border-radius: var(--border-radius); margin: 16px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <div style="margin-bottom: 16px;">
        <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 4px;">{page.name}</h2>
        {f'<p style="color: var(--text-secondary); font-size: 14px;">{page.description}</p>' if page.description else ''}
    </div>
    {content}
</section>"""
    
    def _generate_page_content(self, page: PageNode, layout: str) -> str:
        """生成页面内容"""
        if layout == "table" or "list" in page.name.lower():
            return self._generate_table_content(page)
        elif layout == "form":
            return self._generate_form_content(page)
        elif layout == "detail":
            return self._generate_detail_content(page)
        elif layout == "grid":
            return self._generate_grid_content(page)
        elif layout == "wizard":
            return self._generate_wizard_content(page)
        elif layout == "card":
            return self._generate_card_content(page)
        else:
            return self._generate_default_content(page)
    
    def _generate_table_content(self, page: PageNode) -> str:
        """生成表格内容"""
        attrs = page.entities
        columns = ["序号", "名称", "描述", "状态", "操作"]
        
        header_cells = "".join(f'<th style="padding: 12px; text-align: left; border-bottom: 1px solid var(--border-color); font-weight: 600;">{col}</th>' for col in columns)
        
        rows = ""
        for i in range(1, 4):
            cells = f'<td style="padding: 12px; border-bottom: 1px solid var(--border-color);">{i}</td>'
            cells += f'<td style="padding: 12px; border-bottom: 1px solid var(--border-color);">示例数据 {i}</td>'
            cells += f'<td style="padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">描述信息 {i}</td>'
            cells += '<td style="padding: 12px; border-bottom: 1px solid var(--border-color);"><span style="background: #f6ffed; color: #52c41a; padding: 2px 8px; border-radius: 4px; font-size: 12px;">正常</span></td>'
            cells += '<td style="padding: 12px; border-bottom: 1px solid var(--border-color);"><a href="#" style="color: var(--primary-color); margin-right: 8px;">查看</a><a href="#" style="color: var(--primary-color); margin-right: 8px;">编辑</a><a href="#" style="color: var(--error-color);">删除</a></td>'
            rows += f'<tr>{cells}</tr>'
        
        toolbar = f"""<div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
            <div style="display: flex; gap: 8px;">
                <input type="text" placeholder="搜索..." style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; width: 200px;">
                <button style="padding: 8px 16px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">搜索</button>
            </div>
            <button style="padding: 8px 16px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">+ 新建</button>
        </div>"""
        
        pagination = """<div style="display: flex; justify-content: flex-end; margin-top: 16px; gap: 8px;">
            <button style="padding: 4px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: white; cursor: pointer;">上一页</button>
            <button style="padding: 4px 12px; border: 1px solid var(--primary-color); border-radius: 4px; background: var(--primary-color); color: white; cursor: pointer;">1</button>
            <button style="padding: 4px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: white; cursor: pointer;">2</button>
            <button style="padding: 4px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: white; cursor: pointer;">3</button>
            <button style="padding: 4px 12px; border: 1px solid var(--border-color); border-radius: 4px; background: white; cursor: pointer;">下一页</button>
        </div>"""
        
        return f"""{toolbar}
    <table style="width: 100%; border-collapse: collapse;">
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
    </table>
    {pagination}"""
    
    def _generate_form_content(self, page: PageNode) -> str:
        """生成表单内容"""
        fields = [
            ("名称", "text", "请输入名称"),
            ("描述", "textarea", "请输入描述"),
            ("状态", "select", "请选择状态"),
        ]
        
        form_fields = ""
        for label, type_, placeholder in fields:
            if type_ == "textarea":
                form_fields += f"""<div style="margin-bottom: 16px;">
            <label style="display: block; margin-bottom: 4px; font-weight: 500;">{label}</label>
            <textarea placeholder="{placeholder}" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px; min-height: 80px; font-family: inherit;"></textarea>
        </div>"""
            elif type_ == "select":
                form_fields += f"""<div style="margin-bottom: 16px;">
            <label style="display: block; margin-bottom: 4px; font-weight: 500;">{label}</label>
            <select style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px;">
                <option>{placeholder}</option>
                <option>选项一</option>
                <option>选项二</option>
            </select>
        </div>"""
            else:
                form_fields += f"""<div style="margin-bottom: 16px;">
            <label style="display: block; margin-bottom: 4px; font-weight: 500;">{label}</label>
            <input type="{type_}" placeholder="{placeholder}" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 4px;">
        </div>"""
        
        return f"""<form style="max-width: 600px;">
        {form_fields}
        <div style="display: flex; gap: 8px; margin-top: 24px;">
            <button type="submit" style="padding: 8px 24px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">保存</button>
            <button type="button" style="padding: 8px 24px; background: white; border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer;">取消</button>
        </div>
    </form>"""
    
    def _generate_detail_content(self, page: PageNode) -> str:
        """生成详情内容"""
        return f"""<div style="max-width: 800px;">
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
            <div style="padding: 16px; background: var(--bg-secondary); border-radius: 4px;">
                <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 4px;">名称</div>
                <div style="font-weight: 500;">示例数据名称</div>
            </div>
            <div style="padding: 16px; background: var(--bg-secondary); border-radius: 4px;">
                <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 4px;">状态</div>
                <div><span style="background: #f6ffed; color: #52c41a; padding: 2px 8px; border-radius: 4px; font-size: 12px;">正常</span></div>
            </div>
            <div style="padding: 16px; background: var(--bg-secondary); border-radius: 4px;">
                <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 4px;">创建时间</div>
                <div style="font-weight: 500;">2026-05-04 10:30:00</div>
            </div>
            <div style="padding: 16px; background: var(--bg-secondary); border-radius: 4px;">
                <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 4px;">更新时间</div>
                <div style="font-weight: 500;">2026-05-04 15:20:00</div>
            </div>
        </div>
        <div style="margin-top: 24px;">
            <h3 style="font-size: 16px; margin-bottom: 12px;">描述</h3>
            <p style="color: var(--text-secondary); line-height: 1.6;">这里是详细描述信息，包含业务实体的完整说明和相关配置。</p>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 24px;">
            <button style="padding: 8px 24px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">编辑</button>
            <button style="padding: 8px 24px; background: white; border: 1px solid var(--error-color); color: var(--error-color); border-radius: 4px; cursor: pointer;">删除</button>
            <button style="padding: 8px 24px; background: white; border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer;">返回</button>
        </div>
    </div>"""
    
    def _generate_grid_content(self, page: PageNode) -> str:
        """生成网格内容"""
        cards = ""
        for i in range(1, 5):
            cards += f"""<div style="padding: 20px; background: var(--bg-secondary); border-radius: 4px; cursor: pointer;" onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.12)'" onmouseout="this.style.boxShadow='none'">
                <div style="font-weight: 600; margin-bottom: 8px;">卡片 {i}</div>
                <div style="color: var(--text-secondary); font-size: 14px;">卡片描述内容 {i}</div>
                <div style="margin-top: 12px;"><span style="background: #e6f4ff; color: var(--primary-color); padding: 2px 8px; border-radius: 4px; font-size: 12px;">标签</span></div>
            </div>"""
        
        return f"""<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">
        {cards}
    </div>"""
    
    def _generate_wizard_content(self, page: PageNode) -> str:
        """生成向导内容"""
        steps = """<div style="display: flex; margin-bottom: 24px; position: relative;">
            <div style="position: absolute; top: 12px; left: 40px; right: 40px; height: 2px; background: var(--border-color);"></div>
            <div style="position: relative; text-align: center; flex: 1;">
                <div style="width: 24px; height: 24px; background: var(--primary-color); border-radius: 50%; color: white; line-height: 24px; margin: 0 auto 8px; font-size: 12px;">1</div>
                <div style="font-size: 12px; color: var(--primary-color);">步骤一</div>
            </div>
            <div style="position: relative; text-align: center; flex: 1;">
                <div style="width: 24px; height: 24px; background: var(--primary-color); border-radius: 50%; color: white; line-height: 24px; margin: 0 auto 8px; font-size: 12px;">2</div>
                <div style="font-size: 12px; color: var(--primary-color);">步骤二</div>
            </div>
            <div style="position: relative; text-align: center; flex: 1;">
                <div style="width: 24px; height: 24px; background: var(--border-color); border-radius: 50%; color: var(--text-secondary); line-height: 24px; margin: 0 auto 8px; font-size: 12px;">3</div>
                <div style="font-size: 12px; color: var(--text-secondary);">步骤三</div>
            </div>
        </div>"""
        
        return f"""{steps}
    <div style="padding: 24px; background: var(--bg-secondary); border-radius: 4px;">
        <h3 style="margin-bottom: 16px;">当前步骤内容</h3>
        <p style="color: var(--text-secondary); line-height: 1.6;">这里是当前步骤的表单或操作区域。</p>
        <div style="margin-top: 24px; display: flex; justify-content: flex-end; gap: 8px;">
            <button style="padding: 8px 24px; background: white; border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer;">上一步</button>
            <button style="padding: 8px 24px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">下一步</button>
        </div>
    </div>"""
    
    def _generate_card_content(self, page: PageNode) -> str:
        """生成卡片内容"""
        buttons_html = ""
        if page.operations:
            btns = []
            for op in page.operations[:3]:
                btns.append(
                    f'<button style="padding: 6px 16px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">{op}</button>'
                )
            buttons_html = f'<div style="margin-top: 16px; display: flex; gap: 8px;">{"".join(btns)}</div>'
        
        return f"""<div style="padding: 24px; background: var(--bg-secondary); border-radius: 4px;">
        <h3 style="margin-bottom: 12px;">{page.name}</h3>
        <p style="color: var(--text-secondary); line-height: 1.6;">{page.description or '页面内容区域'}</p>
        {buttons_html}
    </div>"""
    
    def _generate_default_content(self, page: PageNode) -> str:
        """生成默认内容"""
        buttons_html = ""
        if page.operations:
            btns = []
            for op in page.operations[:3]:
                btns.append(
                    f'<button style="padding: 6px 16px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">{op}</button>'
                )
            buttons_html = f'<div style="margin-top: 16px; display: flex; gap: 8px;">{"".join(btns)}</div>'
        
        return f"""<div style="padding: 24px; background: var(--bg-secondary); border-radius: 4px;">
        <p style="color: var(--text-secondary);">页面内容：{page.description or page.name}</p>
        {buttons_html}
    </div>"""
    
    def _generate_page_css(self, page: PageNode) -> str:
        """生成页面 CSS"""
        return f"""/* {page.name} styles */
#{page.id} {{
    background: var(--bg-color);
    border-radius: var(--border-radius);
    margin: 16px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}"""
    
    def _generate_page_js(self, page: PageNode) -> str:
        """生成页面 JS"""
        return f"""// {page.name} interactions
(function() {{
    const page = document.getElementById('{page.id}');
    if (!page) return;
    
    // 绑定交互事件
    page.querySelectorAll('button').forEach(btn => {{
        btn.addEventListener('click', function(e) {{
            console.log('[{page.name}] Button clicked:', e.target.textContent);
        }});
    }});
    
    console.log('[{page.name}] Initialized');
}})();"""
    
    def _generate_default_css(self) -> str:
        """生成默认 CSS"""
        return """/* Default styles */
.container { max-width: 1200px; margin: 0 auto; padding: 0 16px; }
.btn { padding: 8px 16px; border-radius: 4px; border: none; cursor: pointer; }
.btn-primary { background: var(--primary-color); color: white; }
.btn-default { background: white; border: 1px solid var(--border-color); }"""
    
    def _generate_default_js(self) -> str:
        """生成默认 JS"""
        return """// Default interactions
document.addEventListener('DOMContentLoaded', function() {
    console.log('Prototype initialized');
});"""
