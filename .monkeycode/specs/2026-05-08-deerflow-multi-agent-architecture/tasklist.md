# Implementation Task List

## Phase 1: 基础设施 (Infrastructure)

### Task 1.1: 创建 SubAgentRegistry 和配置系统
- [x] 创建 `src/pm_workstation/agents/registry.py`
- [x] 实现 `SubAgentConfig` 数据模型
- [x] 实现 `SubAgentRegistry` 类（注册/注销/查询/匹配）
- [x] 创建 `config/subagents.yaml` 配置文件
- [x] 编写单元测试

### Task 1.2: 实现 TaskDelegationTool 和 SubAgentExecutor
- [x] 创建 `src/pm_workstation/agents/task_tool.py`
- [x] 实现 `TaskDelegationTool` 类（委派/批量委派）
- [x] 实现 `SubAgentExecutor` 类（执行子 Agent 任务）
- [x] 实现 `TaskResult` 和 `SubTask` 数据模型
- [x] 编写单元测试

### Task 1.3: 实现 ContextManager 和上下文隔离
- [x] 创建 `src/pm_workstation/agents/task_tool.py` (ContextManager 已包含在内)
- [x] 实现 `IsolatedContext` 数据模型
- [x] 实现 `ContextManager` 类（创建隔离上下文/合并结果）
- [x] 实现工作空间目录管理
- [x] 编写单元测试

### Task 1.4: 实现 MiddlewareChain 和基础中间件
- [x] 创建 `src/pm_workstation/agents/middlewares/` 目录
- [x] 实现 `Middleware` 抽象基类
- [x] 实现 `MiddlewareChain` 类
- [x] 实现基础中间件：
  - `ContextMiddleware`: 上下文管理
  - `SummarizationMiddleware`: 上下文压缩
  - `ErrorHandlingMiddleware`: 错误处理
  - `StatePersistenceMiddleware`: 状态持久化
  - `AuditMiddleware`: 审计日志
- [x] 编写单元测试

## Phase 2: Coordinator Agent

### Task 2.1: 实现 Coordinator Agent 核心逻辑
- [x] 创建 `src/pm_workstation/agents/coordinator.py`
- [x] 实现 `CoordinatorAgent` 类
- [x] 实现系统提示模板
- [x] 实现 `process_request()` 方法
- [x] 编写单元测试

### Task 2.2: 实现任务拆解逻辑
- [x] 实现 `_decompose_task()` 方法
- [x] 实现 `TaskDecomposition` 数据模型 (已在 Task 1.2 中实现)
- [x] 创建任务拆解提示模板
- [x] 实现结果解析和验证

### Task 2.3: 实现结果汇总逻辑
- [x] 实现 `_delegate_and_collect()` 方法
- [x] 实现并发控制（最多 3 个子任务）
- [x] 实现结果汇总到主上下文
- [x] 处理超时和失败场景

### Task 2.4: 集成现有 LLM 适配层
- [x] 集成 LLMBackend 接口
- [x] 测试 LLM 调用和响应解析
- [x] LLM 失败时使用默认降级方案

## Phase 3: Sub-agent 迁移

### Task 3.1: 将现有 Agent 迁移为 Sub-agent 配置
- [x] 创建 `config/subagents.yaml` 完整配置
- [x] 映射现有 Agent 到新配置：
  - `RequirementParser` -> `analyst`
  - `PRDGenerator` -> `writer`
  - `HuashuPrototypeGenerator` -> `designer`
  - `ConsistencyChecker` -> `qa`
- [x] 更新系统提示模板
- [x] 测试配置加载

### Task 3.2: 创建 Skills 定义文件
- [x] 创建 `skills/` 目录
- [x] 创建技能定义文件：
  - `requirement-analysis.yaml`
  - `prd-generation.yaml`
  - `prototype-generation.yaml`
  - `document-review.yaml`
  - `consistency-check.yaml`
- [x] 实现 `SkillLoader` 类
- [x] 编写单元测试

### Task 3.3: 实现技能按需加载
- [x] 在 `SubAgentExecutor` 中集成技能加载
- [x] 实现技能系统提示注入
- [x] 实现技能工具白名单过滤
- [x] 测试技能加载和执行

### Task 3.4: 测试每个 Sub-agent 独立执行
- [x] 为每个 Sub-agent 编写独立执行测试（通过 TaskDelegationTool 测试覆盖）
- [x] 测试上下文隔离
- [x] 测试超时处理
- [x] 测试错误降级

## Phase 4: 工作流图重构

### Task 4.1: 重构 LangGraph 状态机
- [x] 更新 `src/pm_workstation/orchestrator/workflow_state.py`
  - 添加新字段：`task_decomposition`, `subtask_results`, `active_agents`, `coordinator_summary`
- [x] 创建新的状态机图定义 `workflow_graph_v2.py`
- [x] 保持向后兼容的状态枚举

### Task 4.2: 实现 Coordinator 节点
- [x] 在 `workflow_graph_v2.py` 中添加 `coordinator_node` (WorkflowNodesV2.parsing_node)
- [x] 实现节点执行逻辑
- [x] 集成 CoordinatorAgent
- [x] 测试节点执行

### Task 4.3: 实现动态路由逻辑
- [x] 实现路由函数：`should_proceed_to_generate_v2()`, `should_handle_generate_result_v2()`, `should_proceed_to_complete_v2()`
- [x] 实现条件判断：智能降级到 V1 逻辑
- [x] 测试路由正确性

### Task 4.4: 保持向后兼容的 API
- [x] 验证 API 路由签名不变 (`use_v2` 参数控制)
- [x] 验证响应格式不变
- [x] 测试现有工作流兼容
- [x] 编写向后兼容测试

## Phase 5: 测试和优化

### Task 5.1: 编写单元测试和集成测试
- [x] 补充缺失的单元测试 (test_phase5_supplement.py)
- [x] 编写集成测试 (test_phase3_integration.py, test_phase4_integration.py)
- [x] 确保测试覆盖率 > 80% (当前 81%)
- [x] 运行完整测试套件 (718 passed)

### Task 5.2: 性能测试和优化
- [x] 运行性能测试
- [x] 优化上下文压缩 (SummarizationMiddleware)
- [x] 优化并发执行 (TaskDelegationTool max_concurrent=3)
- [x] 记录性能指标

### Task 5.3: 错误场景测试
- [x] 测试 LLM 失败场景 (Coordinator 降级到 V1)
- [x] 测试超时场景 (Coordinator 120s, Sub-agent 可配置)
- [x] 测试上下文溢出 (SummarizationMiddleware 4000 chars)
- [x] 测试状态恢复 (StatePersistenceMiddleware)

### Task 5.4: 文档更新
- [x] 创建 requirements.md
- [x] 创建 design.md
- [x] 创建 tasklist.md
- [x] 提交到 git 仓库
