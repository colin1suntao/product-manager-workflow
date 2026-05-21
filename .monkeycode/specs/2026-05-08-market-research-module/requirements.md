# 市场调研模块需求文档

## 介绍

市场调研模块是 PM Workstation 的新增功能模块，旨在帮助产品经理快速生成专业的市场调研报告。用户只需输入调研需求描述，系统将自动调用相关的 PM Skills（如 PESTEL 分析、TAM/SAM/SOM 计算、客户旅程图等），生成结构化的市场调研报告。

## 术语表

- **Market Research Module**: 市场调研模块，系统中负责市场调研报告生成的组件
- **PM Skills**: 产品经理技能库，包含 47 个专业 PM 工具和方法论
- **Research Report**: 调研报告，由多个 PM Skills 组合生成的结构化文档
- **Research Template**: 调研模板，预定义的调研场景和技能组合

## 需求

### 需求 1：市场调研入口

**用户故事**: 作为产品经理，我希望能够快速创建市场调研任务，以便分析目标市场和竞争环境。

#### 验收标准

1. WHEN 用户访问 `/market-research` 页面，系统 SHALL 显示市场调研创建表单
2. WHEN 用户输入调研需求描述，系统 SHALL 提供 PM Skills 推荐
3. WHEN 用户提交调研任务，系统 SHALL 创建后台任务并返回任务 ID
4. WHILE 任务执行中，系统 SHALL 提供实时进度更新

### 需求 2：智能技能推荐

**用户故事**: 作为产品经理，我希望系统能根据我的调研需求自动推荐合适的 PM Skills，以便我快速选择合适的分析工具。

#### 验收标准

1. WHEN 用户输入调研需求，系统 SHALL 分析需求关键词并推荐相关 Skills
2. WHEN 推荐的 Skills 包含 PESTEL 分析，系统 SHALL 显示宏观环境分析标签
3. WHEN 推荐的 Skills 包含 TAM/SAM/SOM，系统 SHALL 显示市场规模计算标签
4. IF 用户选择自定义模式，系统 SHALL 显示所有可用的调研相关 Skills

### 需求 3：调研报告生成

**用户故事**: 作为产品经理，我希望系统能根据选中的 PM Skills 自动生成结构化的调研报告。

#### 验收标准

1. WHEN 用户选中多个 PM Skills，系统 SHALL 按顺序调用每个 Skill 生成对应章节
2. WHEN 生成 PESTEL 分析章节，系统 SHALL 输出政治、经济、社会、技术、环境、法律六个维度的分析
3. WHEN 生成 TAM/SAM/SOM 章节，系统 SHALL 输出市场规模计算及假设说明
4. WHEN 生成客户画像章节，系统 SHALL 输出 Proto-Persona 结构化数据
5. WHEN 所有章节生成完成，系统 SHALL 合并为完整的 Markdown 报告

### 需求 4：调研模板管理

**用户故事**: 作为产品经理，我希望能保存常用的调研技能组合为模板，以便快速复用。

#### 验收标准

1. WHEN 用户完成一次调研配置，系统 SHALL 提供"保存为模板"选项
2. WHEN 用户保存模板，系统 SHALL 记录模板名称、描述和技能列表
3. WHEN 用户创建新调研，系统 SHALL 显示已保存的模板列表
4. WHEN 用户选择模板，系统 SHALL 自动填充对应的技能选择

### 需求 5：调研报告查看

**用户故事**: 作为产品经理，我希望查看和管理已生成的调研报告。

#### 验收标准

1. WHEN 用户访问 `/market-research` 页面，系统 SHALL 显示历史调研报告列表
2. WHEN 用户点击某个报告，系统 SHALL 显示报告详情
3. WHEN 报告包含图表数据，系统 SHALL 渲染 Mermaid 或表格
4. WHEN 用户请求导出，系统 SHALL 提供 Markdown 或 PDF 格式下载

## 非功能需求

### 性能需求
- 调研报告生成时间 SHALL 不超过 120 秒（单个 Skill 调用不超过 30 秒）
- 系统 SHALL 支持并发执行至少 5 个调研任务

### 可用性需求
- 调研页面 SHALL 提供清晰的操作指引
- 技能推荐 SHALL 基于用户输入的语义分析，而非简单关键词匹配

### 安全需求
- 调研报告 SHALL 仅对创建者可见
- API 接口 SHALL 验证用户 JWT Token
