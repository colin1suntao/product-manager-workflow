"""样式一致性检查器

检查原型生成的 HTML/CSS 是否符合设计规范。
"""


from pydantic import BaseModel, Field


class StyleIssue(BaseModel):
    """样式问题"""
    severity: str = Field(..., description="严重程度 (error, warning, info)")
    element: str = Field(..., description="元素选择器")
    issue: str = Field(..., description="问题描述")
    suggestion: str = Field(default="", description="修复建议")


class StyleRule(BaseModel):
    """样式规则"""
    name: str = Field(..., description="规则名称")
    css_property: str = Field(..., description="CSS属性")
    expected_value: str = Field(..., description="期望值")
    description: str = Field(default="", description="规则描述")


class StyleConsistencyResult(BaseModel):
    """样式一致性检查结果"""
    passed: bool = Field(..., description="是否通过")
    issues: list[StyleIssue] = Field(default_factory=list, description="问题列表")
    rules_checked: int = Field(default=0, description="检查的规则数")
    rules_passed: int = Field(default=0, description="通过的规则数")


class StyleConsistencyChecker:
    """样式一致性检查器

    检查生成的 HTML/CSS 是否符合设计规范的一致性要求。
    """

    def __init__(self, design_system: dict | None = None):
        self._design_system = design_system or self._get_default_design_system()

    def check(self, html_content: str, css_content: str) -> StyleConsistencyResult:
        """检查样式一致性

        Args:
            html_content: HTML内容
            css_content: CSS内容

        Returns:
            检查结果
        """
        issues = []
        rules_checked = 0
        rules_passed = 0

        # 检查颜色一致性
        color_issues = self._check_colors(css_content)
        issues.extend(color_issues)
        rules_checked += 1
        rules_passed += 1 if not color_issues else 0

        # 检查字体一致性
        font_issues = self._check_fonts(css_content)
        issues.extend(font_issues)
        rules_checked += 1
        rules_passed += 1 if not font_issues else 0

        # 检查间距一致性
        spacing_issues = self._check_spacing(css_content)
        issues.extend(spacing_issues)
        rules_checked += 1
        rules_passed += 1 if not spacing_issues else 0

        # 检查按钮样式
        button_issues = self._check_buttons(html_content, css_content)
        issues.extend(button_issues)
        rules_checked += 1
        rules_passed += 1 if not button_issues else 0

        # 检查表单样式
        form_issues = self._check_forms(html_content, css_content)
        issues.extend(form_issues)
        rules_checked += 1
        rules_passed += 1 if not form_issues else 0

        return StyleConsistencyResult(
            passed=len(issues) == 0,
            issues=issues,
            rules_checked=rules_checked,
            rules_passed=rules_passed,
        )

    def _check_colors(self, css_content: str) -> list[StyleIssue]:
        """检查颜色一致性"""
        issues = []
        primary_color = self._design_system.get("colors", {}).get("primary", "#1677ff")

        # 检查是否使用了非设计规范中的主色
        if "background:" in css_content or "color:" in css_content:
            # 简单检查：查找 hardcode 的颜色值
            import re
            colors_used = re.findall(r'#[0-9a-fA-F]{3,6}', css_content)

            for color in colors_used:
                if color.lower() != primary_color.lower():
                    # 允许常见的中性色
                    neutral_colors = ["#000", "#000000", "#fff", "#ffffff", "#333", "#666", "#999", "#ccc", "#eee", "#f5f5f5"]
                    if color.lower() not in [c.lower() for c in neutral_colors]:
                        issues.append(StyleIssue(
                            severity="warning",
                            element="css",
                            issue=f"使用了非设计规范颜色: {color}",
                            suggestion=f"建议使用设计规范中的主色: {primary_color}",
                        ))

        return issues

    def _check_fonts(self, css_content: str) -> list[StyleIssue]:
        """检查字体一致性"""
        issues = []
        expected_fonts = self._design_system.get("fonts", {}).get("family", "-apple-system, BlinkMacSystemFont, 'Segoe UI'")

        if "font-family" in css_content:
            # 检查是否使用了系统字体栈
            if expected_fonts.split(",")[0].strip() not in css_content:
                issues.append(StyleIssue(
                    severity="info",
                    element="body",
                    issue="未使用推荐的系统字体栈",
                    suggestion=f"建议使用: {expected_fonts}",
                ))

        return issues

    def _check_spacing(self, css_content: str) -> list[StyleIssue]:
        """检查间距一致性"""
        issues = []
        spacing_scale = self._design_system.get("spacing", {}).get("scale", [4, 8, 12, 16, 24, 32])

        import re
        # 查找像素值（排除 border 中的像素值）
        # 先移除 border 相关的声明
        css_without_borders = re.sub(r'border[^:]*:\s*[^;]+;', '', css_content)
        px_values = re.findall(r'(\d+)px', css_without_borders)

        for val in px_values:
            num = int(val)
            if num not in spacing_scale and num != 0:
                # 检查是否接近某个间距值
                closest = min(spacing_scale, key=lambda x: abs(x - num))
                if abs(num - closest) > 2:  # 容忍2px误差
                    issues.append(StyleIssue(
                        severity="warning",
                        element="css",
                        issue=f"使用了非标准间距: {num}px",
                        suggestion=f"建议使用设计规范中的间距值: {spacing_scale}",
                    ))

        return issues

    def _check_buttons(self, html_content: str, css_content: str) -> list[StyleIssue]:
        """检查按钮样式"""
        issues = []

        if "<button" in html_content or 'class="btn' in html_content:
            # 检查按钮是否有统一的样式
            if "border-radius" not in css_content:
                issues.append(StyleIssue(
                    severity="warning",
                    element="button",
                    issue="按钮缺少 border-radius 样式",
                    suggestion="建议统一设置按钮圆角，如: border-radius: 6px",
                ))

            if "cursor: pointer" not in css_content and "cursor:pointer" not in css_content:
                issues.append(StyleIssue(
                    severity="info",
                    element="button",
                    issue="按钮缺少 cursor: pointer 样式",
                    suggestion="添加 cursor: pointer 提升交互体验",
                ))

        return issues

    def _check_forms(self, html_content: str, css_content: str) -> list[StyleIssue]:
        """检查表单样式"""
        issues = []

        if "<input" in html_content or "<form" in html_content:
            # 检查输入框是否有统一的样式
            if "input" in css_content.lower():
                if "border" not in css_content:
                    issues.append(StyleIssue(
                        severity="warning",
                        element="input",
                        issue="输入框缺少 border 样式",
                        suggestion="建议统一设置输入框边框，如: border: 1px solid #d9d9d9",
                    ))

            if "padding" not in css_content:
                issues.append(StyleIssue(
                    severity="info",
                    element="input",
                    issue="输入框缺少 padding 样式",
                    suggestion="建议统一设置输入框内边距，如: padding: 8px 12px",
                ))

        return issues

    def _get_default_design_system(self) -> dict:
        """获取默认设计规范"""
        return {
            "colors": {
                "primary": "#1677ff",
                "success": "#52c41a",
                "warning": "#faad14",
                "error": "#ff4d4f",
                "text": "#000000e0",
                "text_secondary": "#00000073",
                "border": "#d9d9d9",
                "background": "#ffffff",
                "background_secondary": "#f5f5f5",
            },
            "fonts": {
                "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
                "size_base": "14px",
                "size_sm": "12px",
                "size_lg": "16px",
                "size_xl": "20px",
            },
            "spacing": {
                "scale": [4, 8, 12, 16, 24, 32, 48],
            },
            "border_radius": {
                "sm": "4px",
                "md": "6px",
                "lg": "8px",
                "full": "9999px",
            },
        }
