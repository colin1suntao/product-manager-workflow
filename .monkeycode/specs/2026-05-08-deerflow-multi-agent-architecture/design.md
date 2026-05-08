# DeerFlow 2.0 多 Agent 协作架构改造

Feature Name: deerflow-multi-agent-architecture
Updated: 2026-05-08

## Description

以 DeerFlow 2.0 为底座，将 PM Workstation 从固定 4 节点流水线 (parse->generate->verify->complete) 改造为 Coordinator Agent + 动态 Sub-agent 委派模式。新架构支持：

- **智能任务拆解**：Coordinator 自动分析需求并生成任务分解计划
- **动态委派**：根据任务类型选择最合适的 Sub-agent
- **并发执行**：最多 3 个子任务并行执行
- **上下文隔离**：每个子 Agent 拥有独立上下文空间
- **可插拔技能**：通过 Skills 系统扩展 Agent 能力
- **中间件链**：处理横切关注点（上下文管理、错误处理、摘要压缩）

## Architecture

```mermaid
graph TB
    User[用户] --> API[FastAPI Gateway]
    API --> WM[WorkflowManager]
    WM --> LG[LangGraph StateGraph]

    subgraph "Coordinator Layer"
        LG --> CA[Coordinator Agent]
        CA --> MW[Middleware Chain]
    end

    subgraph "Sub-agent Registry"
        MW --> Registry[Agent Registry]
        Registry --> NA[Analyst Agent<br/>需求分析师]
        Registry --> WA[Writer Agent<br/>PRD 写手]
        Registry --> DA[Designer Agent<br/>原型设计师]
        Registry --> RA[Reviewer Agent<br/>文档审阅]
        Registry --> QA[QA Agent<br/>校验员]
    end

    subgraph "Task Delegation"
        CA -->|task()| TaskTool[Task Delegation Tool]
        TaskTool -->|并发≤3| NA
        TaskTool --> WA
        TaskTool --> DA
        TaskTool --> RA
        TaskTool --> QA
    end

    subgraph "Skill System"
        NA --> Skills[Skills Loader]
        WA --> Skills
        DA --> Skills
        RA --> Skills
        QA --> Skills
    end

    subgraph "LLM Layer"
        Skills --> ModelRouter[Model Router]
        ModelRouter --> OA[OpenAI Adapter]
        ModelRouter --> AA[Anthropic Adapter]
        ModelRouter --> FH[Fallback Handler]
    end

    NA -->|结果摘要| CA
    WA -->|结果摘要| CA
    DA -->|结果摘要| CA
    RA -->|结果摘要| CA
    QA -->|结果摘要| CA
    CA -->|汇总结果| WM
```

### 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 模式 | Lead + Sub-agent | 比固定流水线更灵活，支持动态任务分解 |
| 并发限制 | 最多 3 个子任务 | 平衡性能和 Token 消耗 |
| 上下文隔离 | 独立上下文 | 避免信息泄露和 Token 浪费 |
| 状态管理 | LangGraph StateGraph | 保持与现有架构兼容 |
| 技能加载 | 按需加载 | 减少初始上下文大小 |

## Components and Interfaces

### 1. Coordinator Agent

**职责**: 工作流编排的核心 Agent，负责任务拆解、委派、汇总

**接口**:
```python
class CoordinatorAgent:
    def __init__(
        self,
        llm_handler: LLMBackend,
        registry: SubAgentRegistry,
        task_tool: TaskDelegationTool,
    ): ...

    async def process_request(
        self,
        requirement_text: str,
        state: WorkflowState,
    ) -> WorkflowState:
        """处理用户请求，拆解任务并委派执行"""
        ...

    async def _decompose_task(
        self,
        requirement: str,
    ) -> TaskDecomposition:
        """拆解任务，生成子任务列表"""
        ...

    async def _delegate_and_collect(
        self,
        subtasks: list[SubTask],
    ) -> dict[str, Any]:
        """委派子任务并收集结果"""
        ...
```

**系统提示模板**:
```
你是产品经理工作站的协调员。你的职责是：
1. 理解用户需求并拆解为可执行的子任务
2. 选择合适的子 Agent 执行每个子任务
3. 监控进度并处理异常
4. 汇总所有结果并交付给用户

可用的子 Agent 包括：
- Analyst Agent: 需求分析、实体提取、角色识别
- Writer Agent: PRD 文档生成
- Designer Agent: 原型设计
- Reviewer Agent: 文档审阅和质量检查
- QA Agent: 一致性校验和问题检测

委派任务时使用 task() 工具，最多同时委派 3 个子任务。
```

### 2. Sub-agent Registry

**职责**: 管理所有已注册的 Sub-agent，支持动态配置

**数据模型**:
```python
class SubAgentConfig(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str]  # 工具白名单
    skills: list[str]  # 技能列表
    model: str  # 模型配置 (inherit/use_default/specific_model)
    max_turns: int = 50
    timeout_seconds: int = 300

class SubAgentRegistry:
    def __init__(self, config_path: str | None = None): ...

    def register(self, config: SubAgentConfig) -> None: ...
    def unregister(self, agent_id: str) -> None: ...
    def get(self, agent_id: str) -> SubAgentConfig | None: ...
    def list_all(self) -> list[SubAgentConfig]: ...
    def match_by_capability(self, required_capabilities: list[str]) -> list[SubAgentConfig]: ...
```

**配置文件** (`config/subagents.yaml`):
```yaml
subagents:
  analyst:
    name: "需求分析师"
    description: "分析需求，提取实体、角色、流程和规则"
    system_prompt: |
      你是需求分析专家。你的职责是：
      - 识别业务实体及其属性
      - 提取用户角色和权限
      - 分析业务流程和分支
      - 拆解业务规则为规则树
    tools: [read_file, write_file, grep]
    skills: [requirement-analysis, entity-extraction]
    model: inherit
    max_turns: 30
    timeout_seconds: 180

  writer:
    name: "PRD 写手"
    description: "根据需求生成标准 PRD 文档"
    system_prompt: |
      你是产品需求文档撰写专家。你的职责是：
      - 生成结构化的 PRD 文档
      - 包含产品概述、功能需求、非功能需求
      - 编写用户故事和验收标准
    tools: [read_file, write_file]
    skills: [prd-generation, markdown-formatting]
    model: inherit
    max_turns: 40
    timeout_seconds: 240

  designer:
    name: "原型设计师"
    description: "设计高保真 HTML 原型"
    system_prompt: |
      你是 UI/UX 设计专家，擅长生成高保真 HTML 原型。
      你的职责是：
      - 根据需求设计页面结构
      - 生成响应式 HTML/CSS/JS
      - 遵循 huashu-design 反 AI slop 原则
    tools: [read_file, write_file, str_replace]
    skills: [prototype-generation, component-matching]
    model: inherit
    max_turns: 50
    timeout_seconds: 300

  reviewer:
    name: "文档审阅员"
    description: "审阅 PRD 文档质量"
    system_prompt: |
      你是文档质量审查专家。你的职责是：
      - 检查 PRD 的完整性和一致性
      - 验证必需章节是否存在
      - 检查术语使用是否规范
    tools: [read_file, grep]
    skills: [document-review, terminology-check]
    model: inherit
    max_turns: 20
    timeout_seconds: 120

  qa:
    name: "校验员"
    description: "校验原型和文档的一致性"
    system_prompt: |
      你是质量保证专家。你的职责是：
      - 校验原型与 PRD 的一致性
      - 检查原型的 HTML 结构完整性
      - 发现潜在的问题和疏漏
    tools: [read_file, grep, bash]
    skills: [consistency-check, prototype-validation]
    model: inherit
    max_turns: 25
    timeout_seconds: 150
```

### 3. Task Delegation Tool

**职责**: 实现 Coordinator 到 Sub-agent 的任务委派

**接口**:
```python
class TaskDelegationTool:
    def __init__(
        self,
        registry: SubAgentRegistry,
        executor: SubAgentExecutor,
        max_concurrent: int = 3,
    ): ...

    async def invoke(
        self,
        agent_id: str,
        task_description: str,
        context: dict[str, Any],
        timeout: int | None = None,
    ) -> TaskResult:
        """委派任务到指定 Sub-agent"""
        ...

    async def invoke_batch(
        self,
        tasks: list[TaskRequest],
    ) -> list[TaskResult]:
        """批量委派任务（支持并发）"""
        ...
```

**执行器**:
```python
class SubAgentExecutor:
    def __init__(
        self,
        llm_factory: LLMFactory,
        context_manager: ContextManager,
    ): ...

    async def execute(
        self,
        config: SubAgentConfig,
        task: str,
        context: dict[str, Any],
    ) -> str:
        """执行子 Agent 任务"""
        ...
```

### 4. Middleware Chain

**职责**: 处理横切关注点

**中间件列表**:

| 中间件 | 职责 | 执行顺序 |
|--------|------|---------|
| ContextMiddleware | 创建和管理独立上下文 | 1 |
| UploadMiddleware | 注入上传文件 | 2 |
| SummarizationMiddleware | 上下文压缩 | 3 |
| ErrorHandlingMiddleware | 错误捕获和重试 | 4 |
| StatePersistenceMiddleware | 状态持久化 | 5 |
| AuditMiddleware | 审计日志 | 6 |

**接口**:
```python
class Middleware(ABC):
    @abstractmethod
    async def before_agent(
        self,
        state: WorkflowState,
        config: SubAgentConfig,
    ) -> WorkflowState: ...

    @abstractmethod
    async def after_agent(
        self,
        state: WorkflowState,
        result: str,
    ) -> WorkflowState: ...

class MiddlewareChain:
    def __init__(self, middlewares: list[Middleware]): ...

    async def execute_before(
        self,
        state: WorkflowState,
        config: SubAgentConfig,
    ) -> WorkflowState: ...

    async def execute_after(
        self,
        state: WorkflowState,
        result: str,
    ) -> WorkflowState: ...
```

### 5. Skill System

**职责**: 可插拔的技能模块

**技能定义格式** (`skills/requirement-analysis.md`):
```markdown
# Requirement Analysis Skill

## Description
分析用户需求，提取业务实体、角色、流程和规则。

## Tools
- read_file: 读取需求文档
- write_file: 保存分析结果
- grep: 搜索关键词

## Steps
1. 阅读原始需求
2. 识别业务实体及其属性
3. 提取用户角色
4. 分析业务流程
5. 拆解业务规则
6. 输出结构化结果

## Output Format
```json
{
  "entities": [...],
  "roles": [...],
  "flows": [...],
  "rules": {...}
}
```
```

**加载器**:
```python
class SkillLoader:
    def __init__(self, skills_dir: str): ...

    def load(self, skill_name: str) -> Skill: ...
    def list_available(self) -> list[str]: ...

class Skill(BaseModel):
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    steps: list[str]
```

### 6. Context Manager

**职责**: 管理子 Agent 的独立上下文

**接口**:
```python
class ContextManager:
    def __init__(self, workspace_dir: str): ...

    def create_isolated_context(
        self,
        agent_id: str,
        task_id: str,
        shared_data: dict[str, Any],
    ) -> IsolatedContext: ...

    def merge_results(
        self,
        main_context: WorkflowState,
        sub_results: dict[str, Any],
    ) -> WorkflowState: ...

class IsolatedContext:
    agent_id: str
    task_id: str
    messages: list[BaseMessage]
    workspace: Path
    uploads: Path
    outputs: Path
```

## Data Models

### WorkflowState (扩展)

```python
class WorkflowState:
    # 原有字段保持不变
    workflow_run: WorkflowRun
    structured_requirement: StructuredRequirement | None
    reasoning_trace: str
    clarification_questions: list[dict]
    page_structure: PageStructure | None
    prototype_html: str
    prd_document: str
    verification_report: VerificationReport | None
    error_message: str | None
    pause_requested: bool
    user_responses: list[dict]

    # 新增字段
    task_decomposition: TaskDecomposition | None  # 任务分解结果
    subtask_results: dict[str, TaskResult]  # 子任务结果映射
    active_agents: set[str]  # 当前活跃的 Agent ID
    context_snapshots: dict[str, IsolatedContext]  # 上下文快照
```

### TaskDecomposition

```python
class TaskDecomposition(BaseModel):
    plan: str  # 执行计划描述
    subtasks: list[SubTask]
    execution_order: list[str]  # 子任务 ID 列表，支持并行标记

class SubTask(BaseModel):
    id: str
    agent_id: str  # 目标 Agent ID
    description: str  # 任务描述
    input_data: dict[str, Any]  # 输入数据
    expected_output: str  # 期望输出描述
    timeout: int  # 超时时间 (秒)
    can_run_parallel: bool  # 是否可并行
```

### TaskResult

```python
class TaskResult(BaseModel):
    task_id: str
    agent_id: str
    status: Literal["success", "failed", "timeout"]
    output: str | None  # 输出结果
    error: str | None  # 错误信息
    duration: float  # 执行时长 (秒)
    token_usage: dict[str, int]  # Token 使用量
```

## Correctness Properties

### 状态一致性
- 工作流状态转换必须遵循预定义的状态机
- 子任务结果必须正确汇总到主上下文
- 暂停/恢复必须保存和还原完整状态

### 上下文隔离
- 子 Agent 无法访问主 Agent 的对话历史
- 子 Agent 之间互相隔离
- 只有结果摘要被注入主上下文

### 并发安全
- 最多 3 个子任务并行执行
- 任务结果按任务 ID 正确关联
- 超时任务必须被正确终止

## Error Handling

### 错误分类

| 错误类型 | 处理策略 |
|---------|---------|
| LLM API 错误 | 重试 3 次，指数退避，然后降级到备选模型 |
| 子 Agent 超时 | 终止执行，标记为失败，Coordinator 决定下一步 |
| 上下文溢出 | 触发摘要压缩，保留关键信息 |
| 任务委派失败 | 记录错误，Coordinator 选择备选 Agent |
| 技能加载失败 | 使用默认系统提示，跳过技能注入 |

### 降级策略

```python
async def handle_subagent_failure(
    self,
    failed_task: SubTask,
    error: Exception,
) -> FallbackAction:
    """处理子 Agent 失败"""
    if failed_task.retry_count < 3:
        return RetryAction(delay=exponential_backoff(failed_task.retry_count))
    elif self.has_alternative_agent(failed_task.agent_id):
        return DelegateToAlternativeAction(agent_id=self.find_alternative(failed_task))
    else:
        return UseDefaultTemplateAction(template=failed_task.output_template)
```

## Test Strategy

### 单元测试
- Coordinator Agent: 测试任务拆解逻辑和委派决策
- SubAgentRegistry: 测试注册/注销/查询功能
- TaskDelegationTool: 测试任务分发和结果收集
- MiddlewareChain: 测试中间件执行顺序和状态传递
- ContextManager: 测试上下文隔离和结果合并

### 集成测试
- 完整工作流: 从需求提交到交付物生成的端到端测试
- 并发执行: 测试 3 个子任务并行执行的正确性
- 暂停/恢复: 测试状态保存和恢复
- 错误场景: 测试 LLM 失败、超时、上下文溢出的处理

### 性能测试
- 单个工作流执行时间 < 60 秒（不含 LLM 调用）
- 并发 10 个工作流不出现状态污染
- 上下文压缩后 Token 使用量减少 50%+

## Implementation Plan

### Phase 1: 基础设施 (2-3 天)
1. 创建 SubAgentRegistry 和配置系统
2. 实现 TaskDelegationTool 和 SubAgentExecutor
3. 实现 ContextManager 和上下文隔离
4. 实现 MiddlewareChain 和基础中间件

### Phase 2: Coordinator Agent (2-3 天)
1. 实现 Coordinator Agent 核心逻辑
2. 实现任务拆解提示和解析
3. 实现结果汇总逻辑
4. 集成现有 LLM 适配层

### Phase 3: Sub-agent 迁移 (2-3 天)
1. 将现有 Agent 类迁移为 Sub-agent 配置
2. 创建 Skills 定义文件
3. 实现技能按需加载
4. 测试每个 Sub-agent 独立执行

### Phase 4: 工作流图重构 (1-2 天)
1. 重构 LangGraph 状态机
2. 实现 Coordinator 节点
3. 实现动态路由逻辑
4. 保持向后兼容的 API

### Phase 5: 测试和优化 (2-3 天)
1. 编写单元测试和集成测试
2. 性能测试和优化
3. 错误场景测试
4. 文档更新

## References

[^1]: DeerFlow 2.0 Architecture - https://github.com/bytedance/deer-flow
[^2]: LangGraph Documentation - https://langchain-ai.github.io/langgraph/
[^3]: PM Workstation Current Architecture - src/pm_workstation/orchestrator/workflow_graph.py
[^4]: PM Workstation Agents - src/pm_workstation/agents/
[^5]: EARS Requirements Pattern - requirements.md
