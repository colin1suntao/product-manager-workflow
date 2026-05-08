---
name: huashu-design
description: 基于 huashu-design 理念的高保真原型设计方法论，使用 React + Babel 构建可交互的 UI 原型
intent: 将产品需求转化为高保真、可交互的 HTML 原型，遵循 huashu-design 的设计哲学和技术规范
type: workflow
best_for:
  - App 原型设计
  - Dashboard 设计
  - 展示页设计
  - 交互式原型
scenarios:
  - 需要快速生成可交互的产品原型
  - 需要遵循专业设计规范的 UI 设计
  - 需要避免 AI 生成的视觉套路
  - 需要高保真的产品演示
estimated_time: 10-15 分钟
---

# Huashu Design 原型设计方法论

huashu-design 是一种专业的原型设计方法论，强调从真实需求出发，避免 AI 生成的视觉套路，创建高保真、可交互的产品原型。

## 核心设计哲学

### 1. 从 existing context 出发
不要凭空设计，先理解需求和品牌上下文。每个设计决策都应该有明确的理由。

### 2. 反 AI slop
避免以下 AI 默认模式：
- 紫色渐变
- Emoji 图标
- 圆角卡片 + 左 border accent
- SVG 画人脸
- 过度使用阴影和渐变

### 3. 诚实的 Placeholder
没数据就写注释，不要编造假数据；没图标就留灰色方块 + 文字标签。

### 4. 系统优先，不要填充
每个元素都必须 earn its place，空白是设计问题，用构图解决。

## 技术架构

### React + Babel 配置
在 HTML 的 `<head>` 中必须包含以下固定版本的 script 标签：

```html
<script src="https://unpkg.com/react@18.3.1/umd/react.development.js" integrity="sha384-hD6/rw4ppMLGNu3tX5cjIb+uRZ7UkRJ6BPkLpg4hAu/6onKUg4lLsHAs9EBPT82L" crossorigin="anonymous"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js" integrity="sha384-u6aeetuaXnQ38mYT8rp6sbXaQe3NL9t+IBXmnYxwkUI2Hw4bsp2Wvmx4yRQF1uAm" crossorigin="anonymous"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" integrity="sha384-m08KidiNqLdpJqLq95G/LEi8Qvjl/xUYll3QILypMoQ65QorJ9Lvtp2RXYGBFj1y" crossorigin="anonymous"></script>
```

### 三条不可违反的规则

1. **styles 对象必须唯一命名**
   - 禁止使用 `const styles = {...}`
   - 必须用唯一前缀如 `const homeStyles = {...}` 或 `const dashboardStyles = {...}`

2. **Scope 不共享**
   - 每个 `<script type="text/babel">` 之间 scope 不通
   - 必须用 `Object.assign(window, {ComponentName})` 导出组件

3. **禁止使用 scrollIntoView**
   - 会搞坏容器滚动
   - 使用 `container.scrollTop = target.offsetTop` 替代

## 正向设计指南

### 排版
- 使用 `text-wrap: pretty` + CSS Grid + 高级 CSS 排版细节
- 使用有特点的 display + body 字体配对，避免 Inter/Roboto/Arial
- 中文排印使用「」引号，不是 ""

### 颜色
- 使用 oklch() 或品牌色，不凭空发明新颜色
- 保持色彩系统的一致性

### 细节
- 一个细节做到 120%，其他做到 80%
- 品味 = 在合适的地方足够精致

### 信息密度分型

**克制型（默认）**：
- 少一层容器
- 少一个 border
- 少一个装饰性 icon
- 给内容留气口

**高密度型（AI/数据类产品）**：
- 每屏至少 3 处可见的产品差异化信息
- 非装饰性数据
- 状态推断
- 上下文关联

## 交互要求

1. **按钮反馈**：点击有反馈效果（hover、active 状态）
2. **表单验证**：有输入验证和提交动画
3. **导航切换**：可以切换不同视图/页面（用 React state 管理）
4. **数据持久化**：使用 localStorage 模拟数据持久化（如果需要）
5. **可点击原型**：App 原型必须可点击、可交互，不是静态摆拍

## 内容要求

1. **真实模拟数据**：填充真实的模拟数据（不要用"Lorem ipsum"）
2. **贴合需求**：页面标题和模块标题要贴合用户需求
3. **功能完整**：功能模块要完整，不要只写占位符
4. **真实图片**：App 原型默认去取真实图片（Wikimedia Commons、Unsplash、Met Museum）

## 文件结构

默认使用单文件架构（所有 JSX inline 写在 `<script type="text/babel">` 中），除非：
- 单文件 >1000 行难维护 → 拆成外部文件并用 HTTP server
- 需要多 agent 并行 → 每屏独立 HTML + iframe 聚合

## 设计检查清单

在交付原型前，检查以下项目：

- [ ] 是否遵循 huashu-design 反 AI slop 原则？
- [ ] styles 对象是否使用唯一命名？
- [ ] 是否避免了 scrollIntoView？
- [ ] 交互是否真实可点击？
- [ ] 数据是否为真实模拟数据？
- [ ] 图片是否使用真实来源？
- [ ] 字体是否使用有特点的配对？
- [ ] 色彩是否使用 oklch() 或品牌色？
- [ ] 信息密度是否符合产品类型？
- [ ] 是否有至少一个 120% 的细节设计？
