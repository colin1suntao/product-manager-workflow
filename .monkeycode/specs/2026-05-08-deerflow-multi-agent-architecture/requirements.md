# Requirements Document

## Introduction

以 DeerFlow 2.0 架构为底座，将现有 PM Workstation 从固定流水线模式改造为多 Agent 协作开发模式。新架构采用 Lead Agent (Coordinator) + 动态 Sub-agent 委派模式，实现更灵活、可扩展的产品管理工作流系统。

## Glossary

- **Coordinator Agent**: 核心编排 Agent，负责理解用户需求、拆解任务、委派给子 Agent、汇总结果
- **Sub-agent**: 子 Agent，执行特定专业任务（需求分析、PRD 编写、原型设计、文档审阅、校验）
- **Task Tool**: 任务委派工具，Coordinator 通过此工具向 Sub-agent 委派工作
- **Skill**: 可插拔的技能模块，定义 Agent 的能力和工具集
- **Middleware**: 中间件组件，处理上下文管理、错误处理、摘要压缩等横切关注点
- **LangGraph**: 工作流编排框架，用于构建状态机和 Agent 图

## Requirements

### Requirement 1: Coordinator Agent (Lead Agent)

**User Story:** AS 产品经理, I WANT 一个智能协调员来自动拆解和分配任务, SO THAT 我不需要手动管理每个工作步骤

#### Acceptance Criteria

1. WHEN 用户提交需求描述, the Coordinator Agent SHALL 分析需求并生成任务分解计划
2. WHEN Coordinator Agent 收到任务, the Coordinator Agent SHALL 根据任务类型选择合适的 Sub-agent 委派执行
3. WHILE Sub-agent 正在执行任务, the Coordinator Agent SHALL 监控进度并处理异常情况
4. IF Sub-agent 执行失败, the Coordinator Agent SHALL 尝试重试或降级到备选方案
5. WHEN 所有子任务完成, the Coordinator Agent SHALL 汇总结果并更新工作流状态

### Requirement 2: Sub-agent Registry and Configuration

**User Story:** AS 系统管理员, I WANT 可配置的 Sub-agent 注册表, SO THAT 我可以灵活添加、移除或修改子 Agent 的能力

#### Acceptance Criteria

1. WHEN 系统启动, the Sub-agent Registry SHALL 加载所有已注册的 Sub-agent 配置
2. WHEN Coordinator Agent 需要委派任务, the Sub-agent Registry SHALL 返回匹配的可用 Sub-agent 列表
3. IF 用户添加新的 Sub-agent 配置, the Sub-agent Registry SHALL 动态注册该 Agent 而无需重启系统
4. EACH Sub-agent SHALL 定义独立的系统提示、工具白名单、模型配置和超时设置

### Requirement 3: Task Delegation Tool

**User Story:** AS Coordinator Agent, I WANT 任务委派工具, SO THAT 我可以向 Sub-agent 发送任务并获取结果

#### Acceptance Criteria

1. WHEN Coordinator Agent 调用 task() 工具, the Task Delegation Tool SHALL 创建子任务并分发给目标 Sub-agent
2. WHILE 子任务正在执行, the Task Delegation Tool SHALL 支持最多 3 个子任务并发执行
3. WHEN 子任务完成, the Task Delegation Tool SHALL 将结果摘要返回给 Coordinator Agent
4. IF 子任务超时, the Task Delegation Tool SHALL 终止执行并返回错误信息
5. WHEN Coordinator Agent 委派任务, the Task Delegation Tool SHALL 为每个子 Agent 创建独立的上下文

### Requirement 4: Middleware Chain

**User Story:** AS 系统开发者, I WANT 可组合的中间件链, SO THAT 我可以处理横切关注点如上下文管理、错误处理、摘要压缩

#### Acceptance Criteria

1. WHEN Agent 执行任务, the Middleware Chain SHALL 按顺序执行所有注册的中间件
2. WHILE 对话历史接近 Token 限制, the SummarizationMiddleware SHALL 压缩上下文并保留关键信息
3. IF Agent 执行出错, the ErrorHandlingMiddleware SHALL 捕获异常并触发重试或降级
4. WHEN 工作流状态变化, the StatePersistenceMiddleware SHALL 保存状态到持久化存储
5. EACH 中间件 SHALL 支持独立启用/禁用配置

### Requirement 5: Skill System

**User Story:** AS 产品经理, I WANT 可插拔的技能系统, SO THAT 我可以根据项目需求启用不同的能力组合

#### Acceptance Criteria

1. WHEN 系统启动, the Skill Loader SHALL 扫描并加载所有已配置的技能
2. WHEN Coordinator Agent 需要特定能力, the Skill System SHALL 按需加载对应技能到上下文
3. IF 技能执行失败, the Skill System SHALL 返回错误并允许 Coordinator 选择备选方案
4. EACH 技能 SHALL 定义为独立的 Markdown 文件,包含系统提示、工具列表和执行步骤

### Requirement 6: Context Isolation

**User Story:** AS 系统架构师, I WANT 子 Agent 上下文隔离, SO THAT 每个子 Agent 只能访问任务相关的数据

#### Acceptance Criteria

1. WHEN Sub-agent 被委派任务, the Context Manager SHALL 创建独立的上下文空间
2. WHILE Sub-agent 执行任务, the Context Manager SHALL 隔离主 Agent 和其他子 Agent 的对话历史
3. WHEN 子任务完成, the Context Manager SHALL 将结果摘要注入主上下文
4. IF 子 Agent 尝试访问未授权数据, the Context Manager SHALL 拒绝并记录审计日志

### Requirement 7: Workflow Graph Refactoring

**User Story:** AS 系统开发者, I WANT 重构 LangGraph 工作流图, SO THAT 它支持 Coordinator + Sub-agent 模式而非固定流水线

#### Acceptance Criteria

1. WHEN 工作流启动, the New Workflow Graph SHALL 首先调用 Coordinator Agent 节点
2. WHILE Coordinator Agent 执行中, the Workflow Graph SHALL 支持动态路由到不同 Sub-agent
3. WHEN 所有子任务完成, the Workflow Graph SHALL 汇总结果并进入校验阶段
4. IF 用户请求暂停, the Workflow Graph SHALL 保存当前状态并等待恢复

### Requirement 8: Backward Compatibility

**User Story:** AS 现有用户, I WANT 向后兼容的 API 接口, SO THAT 我的前端和集成无需修改即可工作

#### Acceptance Criteria

1. WHEN 前端调用工作流 API, the New System SHALL 保持与现有 API 签名完全一致
2. WHILE 工作流执行中, the New System SHALL 返回相同格式的状态和交付物响应
3. IF 旧版配置存在, the New System SHALL 自动迁移到新架构配置
4. EACH 现有工作流状态枚举 SHALL 保持不变并正确映射到新状态机
