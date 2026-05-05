# 系统架构

## 架构概览

PM Workstation 采用前后端分离架构，后端基于 Python FastAPI 提供 RESTful API，前端基于 Next.js 16 App Router 构建用户界面。系统核心通过 LangGraph 状态机编排多个 AI Agent 协作完成需求到交付物的全流程。

```mermaid
graph TB
    subgraph Frontend["前端 (Next.js 16)"]
        F1["React 组件"]
        F2["App Router 页面"]
        F3["API Client"]
    end

    subgraph Backend["后端 (FastAPI)"]
        A1["认证模块 (JWT)"]
        A2["API 路由层"]
        A3["工作流编排器 (LangGraph)"]
        A4["需求解析 Agent"]
        A5["原型生成模块"]
        A6["文档生成模块"]
        A7["校验模块"]
        A8["模型路由器"]
        A9["集成适配器"]
        A10["存储层"]
    end

    subgraph Infrastructure["基础设施"]
        DB["PostgreSQL/SQLite"]
        RD["Redis"]
        S3["MinIO/S3"]
        LLM["OpenAI / Anthropic API"]
    end

    F1 --> F3
    F2 --> F3
    F3 -->|"HTTP /api/v1/*"| A2
    A2 --> A1
    A2 --> A3
    A3 --> A4
    A3 --> A5
    A3 --> A6
    A3 --> A7
    A4 --> A8
    A5 --> A8
    A6 --> A8
    A8 --> LLM
    A3 --> A9
    A3 --> A10
    A2 --> DB
    A1 --> DB
    A1 --> RD
    A10 --> S3
```

## 分层架构

### 1. 表示层 (Presentation Layer)

**前端**: Next.js 16 App Router，使用 React 19 + TypeScript + TailwindCSS 4

| 页面路由 | 功能 |
|---------|------|
| `/workflows` | 工作流管理（创建、查看、暂停、恢复） |
| `/requirements` | 需求解析结果展示 |
| `/prototypes` | 原型预览和编辑 |
| `/documents` | PRD 文档查看 |
| `/integrations` | 外部系统集成配置 |
| `/reports` | 校验报告查看 |
| `/components-lib` | 组件库浏览 |

### 2. API 层 (API Layer)

FastAPI 应用通过路由组组织，所有业务 API 均挂载在 `/api/v1` 前缀下：

| 路由前缀 | 模块 | 认证要求 |
|---------|------|---------|
| `/api/v1/auth/*` | 认证（注册、登录、刷新、登出、改密） | 公开/部分需认证 |
| `/api/v1/workflows/*` | 工作流管理 | 需要 JWT |
| `/api/v1/components/*` | 组件库 | 需要 JWT |
| `/api/v1/integrations/*` | 集成配置和同步任务 | 需要 JWT |
| `/health` | 健康检查 | 公开 |

应用通过 `create_app()` 工厂函数创建，使用 lifespan 管理 `WorkflowManager` 的生命周期。

### 3. 业务逻辑层 (Business Logic Layer)

#### 3.1 认证模块 (`auth/`)

基于 JWT 的双 Token 机制：

```mermaid
graph LR
    A["用户请求"] --> B["OAuth2PasswordBearer"]
    B --> C["get_current_user 依赖"]
    C --> D["verify_access_token"]
    D --> E["提取 user_id"]
    E --> F["路由处理器"]
    
    style A fill:#e1f5fe
    style F fill:#e1f5fe
```

**核心组件**:

- **JWT 工具** (`jwt.py`): Token 签发（access/refresh）、解码、验证
- **UserStore** (`user_store.py`): 用户 CRUD，bcrypt 密码哈希
- **TokenStore** (`token_store.py`): Refresh Token 撤销黑名单（内存实现，生产应使用 Redis）
- **认证依赖** (`dependencies.py`): `get_current_user`（强制认证）、`get_current_user_optional`（可选认证）

**Token 流程**:

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as API /auth
    participant J as JWT 模块
    participant US as UserStore
    participant TS as TokenStore

    U->>A: POST /auth/register (email, password)
    A->>US: create_user()
    US-->>A: User
    A-->>U: UserResponse

    U->>A: POST /auth/login (email, password)
    A->>US: find_by_email()
    US-->>A: User
    A->>A: verify_password()
    A->>J: create_access_token(user_id)
    A->>J: create_refresh_token(user_id)
    J-->>A: (access_token, (refresh_token, jti))
    A-->>U: TokenPair

    U->>A: POST /auth/refresh (refresh_token)
    A->>J: verify_refresh_token()
    J->>TS: is_revoked(jti)?
    TS-->>J: false
    J-->>A: payload
    A->>J: create_access_token(user_id)
    J-->>A: new_access_token
    A-->>U: {access_token, token_type, expires_in}

    U->>A: POST /auth/logout (refresh_token)
    A->>J: verify_refresh_token()
    J-->>A: payload {jti, exp}
    A->>TS: revoke_token(jti, expires_at)
    A-->>U: {message: "登出成功"}
```

#### 3.2 工作流编排层 (`orchestrator/`)

基于 LangGraph StateGraph 实现的状态机，定义完整的工作流生命周期：

```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> PARSING: 启动工作流
    PARSING --> PARSED: 解析完成
    PARSING --> WAITING_USER_INPUT: 需要澄清
    WAITING_USER_INPUT --> PARSING: 用户回复
    PARSED --> GENERATING: 进入生成
    GENERATING --> GENERATED: 生成完成
    GENERATING --> WAITING_USER_INPUT: 暂停请求
    GENERATED --> VERIFYING: 进入校验
    VERIFYING --> VERIFIED: 校验通过
    VERIFYING --> FAILED: 校验失败
    VERIFIED --> COMPLETED: 完成
    COMPLETED --> [*]
    PARSING --> FAILED: 解析错误
    GENERATING --> FAILED: 生成错误
    FAILED --> [*]
```

**核心组件**:

- **WorkflowState** (`workflow_state.py`): LangGraph 状态，携带工作流运行记录、结构化需求、原型 HTML、PRD 文档、校验报告等
- **WorkflowNodes** (`workflow_graph.py`): 定义 parse/generate/verify/complete/handle_user_input 五个节点
- **WorkflowManager** (`workflow_manager.py`): 高层管理接口，提供 start/pause/resume/list/get_deliverables 等操作

#### 3.3 需求解析层 (`agents/`)

通过 LLM 从自然语言需求文本中提取结构化信息：

- **RequirementParser**: 主解析器，调用 LLM 提取业务实体、用户角色、操作流程、业务规则树、边界场景、澄清问题
- 子分析器: `entity_extractor`, `role_identifier`, `rule_decomposer`, `branch_analyzer`, `gap_detector`, `clarification_generator`, `reasoning_tracer`

#### 3.4 原型生成层 (`prototype/`)

- **PageStructureGenerator**: 从结构化需求生成页面结构树（PageNode 层级）
- **ComponentMatcher**: 根据页面需求匹配组件库中的组件
- **HTMLGenerator**: 生成 HTML/CSS/JS 原型代码
- **InteractionConfigurator**: 配置页面交互逻辑

#### 3.5 文档生成层 (`document/`)

- **ContentGenerator**: 基于结构化需求生成 PRD 内容
- **StructureGenerator**: 生成文档结构骨架
- **MarkdownFormatter**: Markdown 格式化和标题提取
- **TemplateEngine**: 文档模板渲染
- **TerminologyChecker**: 术语一致性检查

#### 3.6 校验层 (`verification/`)

多维度校验体系：

```mermaid
graph TB
    subgraph Prototype["原型校验"]
        P1["PageCoverageChecker: 页面覆盖率"]
        P2["InteractionVerifier: 交互逻辑"]
        P3["导航完整性检查"]
    end

    subgraph Document["文档校验"]
        D1["DocumentFormatChecker: 格式规范"]
        D2["DocumentStructureChecker: 结构完整性"]
        D3["TerminologyConsistencyChecker: 术语一致性"]
    end

    subgraph Consistency["一致性检查"]
        C1["实体覆盖一致性"]
        C2["流程覆盖一致性"]
        C3["术语使用一致性"]
        C4["页面-文档对齐"]
    end

    subgraph AutoFix["自动修复"]
        F1["空链接移除"]
        F2["代码块闭合"]
        F3["表格分隔行修复"]
        F4["标题层级修正"]
        F5["断裂导航链接修复"]
    end

    P1 --> R["IssueReporter: 综合报告"]
    P2 --> R
    D1 --> R
    D2 --> R
    C1 --> R
    C2 --> R
    F1 --> R
    F2 --> R
```

#### 3.7 模型路由层 (`model_router/`)

- **LLMBackend**: 抽象基类，定义 chat/chat_stream 接口
- **OpenAIAdapter / AnthropicAdapter**: 具体实现
- **FallbackHandler**: 模型故障时自动降级到备用模型
- **ModelSelector**: 根据任务类型选择最优模型
- **CostOptimizer**: 成本优化策略
- **TaskClassifier**: 任务分类器

#### 3.8 集成层 (`integrations/`)

适配器模式实现外部系统集成：

```mermaid
graph TB
    Registry["AdapterRegistry"] --> Jira["JiraAdapter"]
    Registry --> Figma["FigmaAdapter"]
    Registry --> GitHub["GitHubAdapter"]
    Registry --> GitLab["GitLabAdapter"]
    Registry --> Feishu["FeishuAdapter"]
    Registry --> Trello["TrelloAdapter"]
    Registry --> Sketch["SketchAdapter"]
    
    IntegrationStore --> Registry
    SyncTaskStore --> Registry
```

- **IntegrationConfig**: 集成配置模型（API 端点、密钥、Token）
- **SyncTask**: 同步任务模型（支持 import/export/bidirectional）
- **IntegrationStore / SyncTaskStore**: 内存存储（生产应使用数据库）

#### 3.9 存储层 (`storage/`)

- **StorageBackend**: 抽象接口（upload/download/delete/get_url/exists）
- **LocalStorage**: 本地文件系统实现
- **MinioStorage**: MinIO/S3 对象存储实现
- **StorageFactory**: 根据配置类型创建对应存储后端

### 4. 数据层 (Data Layer)

| 存储 | 用途 | 实现 |
|-----|------|------|
| PostgreSQL/SQLite | 用户数据、工作流元数据 | SQLAlchemy 2.0 ORM |
| Redis | Token 撤销、缓存、消息队列 | redis-py |
| MinIO/S3 | 交付物存储（原型 HTML、PRD 文档） | minio-py / boto3 |
| 内存字典 | 工作流运行记录、集成配置、组件库 | Python dict |

## 数据流

### 完整工作流数据流

```mermaid
sequenceDiagram
    participant C as 客户端
    participant API as API 层
    participant WM as WorkflowManager
    participant WG as LangGraph Workflow
    participant RP as RequirementParser
    participant PSG as PageStructureGenerator
    participant DG as DocumentGenerator
    participant PV as PrototypeVerifier
    participant DV as DocumentVerifier
    participant CC as ConsistencyChecker
    participant AF as AutoFixer
    participant IR as IssueReporter

    C->>API: POST /api/v1/workflows (requirement_text)
    API->>WM: start_workflow(user_id, requirement_text)
    WM->>WG: invoke(initial_state)
    
    WG->>WG: parse 节点
    WG->>RP: parse(requirement_text)
    RP-->>WG: StructuredRequirement
    
    alt 需要澄清
        WG-->>API: WAITING_USER_INPUT + questions
        API-->>C: 返回待澄清问题
        C->>API: POST /api/v1/workflows/{id}/resume (responses)
        API->>WM: resume_workflow()
        WM->>WG: 继续执行
    end
    
    WG->>WG: generate 节点
    WG->>PSG: generate(structured_requirement)
    PSG-->>WG: PageStructure
    WG->>DG: generate(structured_requirement)
    DG-->>WG: PRD Document
    
    WG->>WG: verify 节点
    WG->>PV: verify(requirement, page_structure)
    PV-->>WG: PrototypeVerificationReport
    WG->>DV: verify(document_content)
    DV-->>WG: DocumentVerificationReport
    WG->>CC: check(requirement, page_structure, document)
    CC-->>WG: ConsistencyCheckResult
    
    opt 自动修复
        WG->>AF: fix_document() / fix_prototype()
        AF-->>WG: FixResult
    end
    
    WG->>IR: generate_report(all_results)
    IR-->>WG: VerificationReport
    
    WG-->>WM: COMPLETED state
    WM-->>API: WorkflowRun
    API-->>C: WorkflowResponse
```

## 认证架构

### JWT Token 机制

系统采用 Access Token + Refresh Token 双 Token 机制：

| Token 类型 | 有效期 | 用途 | 撤销机制 |
|-----------|--------|------|---------|
| Access Token | 15 分钟 | API 请求认证 | 过期自动失效 |
| Refresh Token | 7 天 | 获取新的 Access Token | JTI 黑名单 |

**安全特性**:

- 密码使用 bcrypt 哈希存储（限制最大 72 字节）
- Refresh Token 包含唯一 JTI（JWT ID）用于撤销
- 登出时将 Refresh Token 的 JTI 加入黑名单
- 修改密码时撤销所有已签发的 Refresh Token
- 密码长度要求 8-128 字符

**认证流程状态图**:

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Authenticated: 登录成功
    Authenticated --> TokenExpired: Access Token 过期
    TokenExpired --> Authenticated: 刷新 Token 成功
    TokenExpired --> Unauthenticated: 刷新 Token 失败/已撤销
    Authenticated --> Unauthenticated: 登出
    Authenticated --> Unauthenticated: 修改密码(撤销所有 Token)
```

## 部署架构

```mermaid
graph TB
    subgraph Docker["Docker Compose"]
        FE["Frontend (Next.js:3000)"]
        BE["Backend (FastAPI:8000)"]
        PG["PostgreSQL:5432"]
        RD["Redis:6379"]
        MN["MinIO:9000/9001"]
    end

    User["用户浏览器"] -->|"http://localhost:3000"| FE
    FE -->|"http://backend:8000"| BE
    BE --> PG
    BE --> RD
    BE --> MN
```

各服务通过 `pm-network` 桥接网络通信，数据库和 Redis 配置了健康检查确保启动顺序。
