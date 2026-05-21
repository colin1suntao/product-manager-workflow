# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[Sandbox 执行环境实现]
- Date: 2026-05-21
- Context: Agent 在实现 AI Agent Sandbox 功能时发现
- Category: 代码结构
- Instructions:
  - Sandbox 执行环境位于 `src/pm_workstation/sandbox/`
  - SandboxEngine 负责创建执行上下文、协调工具调用、收集产物
  - ToolManager 注册 12 个内置工具：file(6), shell(2), python(2), http(2)
  - ProcessExecutor 执行 Shell 命令和 Python 代码，支持超时控制
  - WorkspaceManager 管理工作区文件，路径为 `/tmp/sandbox/{execution_id}/`
  - SecurityController 验证安全性：阻止危险命令(rm/sudo/shutdown)、内网访问(localhost/127.0.0.1/10.x)、路径穿越(..)
  - ResourceMonitor 监控资源使用：CPU 60s、内存 512MB、文件 10MB
  - API 路由：`/api/v1/sandbox/executions/*`, `/api/v1/sandbox/tools/*`
  - 与 Sub-Agent 集成：Agent 可通过 SandboxEngine.invoke_tool() 调用工具
  - 与 Workflow 集成：Workflow 步骤可在 Sandbox 中执行并收集产物
  - 安全测试通过：所有危险操作均被阻止

[Sub-Agent 注册机制]
- Date: 2026-05-21
- Context: Agent 在实现 DeerFlow 对比优化时发现
- Category: 代码结构
- Instructions:
  - SubAgentRegistry 位于 `src/pm_workstation/agents/sub_agent_registry.py`
  - 8 个 PM Sub-Agent：prototype-designer, requirement-analyst, prd-writer, market-researcher, user-researcher, strategy-advisor, data-analyst, quality-checker
  - 每个 Sub-Agent 有能力标签(capabilities)、默认技能(default_skills)、超时配置(timeout)
  - SubAgentExecutor 执行任务，支持上下文隔离(IsolatedContext)、超时控制、重试机制
  - 注册函数：`register_pm_sub_agents()` 在应用启动时调用
  - API 路由：`/api/v1/chat/sub-agents`, `/api/v1/chat/sub-agents/match`

[Workflow 编排系统]
- Date: 2026-05-21
- Context: Agent 在实现 DeerFlow 对比优化时发现
- Category: 代码结构
- Instructions:
  - WorkflowOrchestrator 位于 `src/pm_workstation/workflow/workflow_orchestrator.py`
  - 7 个预定义 PM Workflow：full-product-design(4步), quick-prototype(2), market-research-full(4), user-research-flow(3), feature-spec(3), business-model-design(3), data-analysis-flow(3)
  - 支持步骤依赖(depends_on)、并行执行(parallel_with)、超时控制、进度追踪
  - WorkflowDefinition 包含步骤定义、估算时间、适用场景、标签
  - API 路由：`/api/v1/workflow-templates/*`, `/api/v1/workflow-templates/{id}/execute`

[产物管理系统]
- Date: 2026-05-21
- Context: Agent 在实现 DeerFlow 对比优化时发现
- Category: 代码结构
- Instructions:
  - ArtifactManager 位于 `src/pm_workstation/artifact/artifact_manager.py`
  - 支持产物类型：prototype(HTML), document(Markdown), report(Markdown), image(PNG/SVG), data(JSON/CSV), code(Python/JS)
  - 版本管理：每次更新创建新版本，支持版本对比(difflib)、回滚
  - 存储路径：`/tmp/artifacts/`，包含 metadata 和 content 子目录
  - API 路由：`/api/v1/artifact-manager/*`

[流式响应 SSE API]
- Date: 2026-05-21
- Context: Agent 在实现 DeerFlow 对比优化时发现
- Category: 代码结构
- Instructions:
  - StreamingChatRouter 位于 `src/pm_workstation/api/routes/streaming_chat.py`
  - SSE 事件类型：intent_analysis, task_routing, skill_loading, chunk, thinking, token_usage, done
  - API 路由：`POST /api/v1/chat/sessions/{id}/stream`
  - 前端通过 EventSource 或 fetch 接收 SSE 流