# API 接口与数据库 Schema

## REST API

所有 API 端点均挂载在 `/api/v1` 前缀下（健康检查端点除外）。

### 认证模块 (`/api/v1/auth`)

#### POST /api/v1/auth/register

注册新用户。

**请求体**:

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| email | string | EmailStr 格式 | 用户邮箱，唯一 |
| password | string | 8-128 字符 | 密码 |

**响应** (`201`):

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-05-05T10:00:00",
  "updated_at": "2026-05-05T10:00:00"
}
```

**错误响应**:
- `400`: 邮箱已被注册

---

#### POST /api/v1/auth/login

用户登录并获取 Token 对。

**请求体**:

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**响应** (`200`):

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**错误响应**:
- `401`: 邮箱或密码错误

---

#### POST /api/v1/auth/refresh

使用 Refresh Token 获取新的 Access Token。

**请求体**:

```json
{
  "refresh_token": "eyJ..."
}
```

**响应** (`200`):

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**错误响应**:
- `401`: 未提供刷新令牌 / 无效的刷新令牌

---

#### POST /api/v1/auth/logout

登出并使 Refresh Token 失效。

**请求体**:

```json
{
  "refresh_token": "eyJ..."
}
```

**响应** (`200`):

```json
{
  "message": "登出成功"
}
```

**错误响应**:
- `401`: 未提供刷新令牌 / 无效的刷新令牌

---

#### POST /api/v1/auth/password

修改当前用户密码（需要认证）。

**请求头**: `Authorization: Bearer <access_token>`

**请求体**:

```json
{
  "old_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| old_password | string | 非空 | 旧密码 |
| new_password | string | 8-128 字符 | 新密码 |

**响应** (`200`):

```json
{
  "message": "密码修改成功"
}
```

**错误响应**:
- `401`: 旧密码不正确
- `404`: 用户不存在

---

### 工作流模块 (`/api/v1/workflows`)

所有工作流端点需要 JWT 认证（`Authorization: Bearer <access_token>`）。

#### POST /api/v1/workflows

启动新的工作流。

**请求体**:

```json
{
  "requirement_text": "我需要做一个用户管理系统，支持注册、登录、权限管理..."
}
```

**响应** (`200`):

```json
{
  "id": "wf-abc123",
  "user_id": "user-uuid",
  "requirement_text": "我需要做一个用户管理系统...",
  "status": "init",
  "created_at": "2026-05-05T10:00:00",
  "updated_at": "2026-05-05T10:00:00",
  "structured_requirement": null,
  "prototype_url": null,
  "prd_document_url": null,
  "error_message": null
}
```

---

#### GET /api/v1/workflows

列出当前用户的所有工作流。

**响应** (`200`):

```json
{
  "workflows": [
    {
      "id": "wf-abc123",
      "user_id": "user-uuid",
      "requirement_text": "...",
      "status": "completed",
      "created_at": "2026-05-05T10:00:00",
      "updated_at": "2026-05-05T10:05:00",
      "structured_requirement": { ... },
      "prototype_url": "prototype.html",
      "prd_document_url": "prd.md",
      "error_message": null
    }
  ],
  "total": 1
}
```

---

#### GET /api/v1/workflows/{workflow_id}

查询指定工作流状态。

**响应** (`200`): 同上 WorkflowResponse

**错误响应**:
- `404`: 工作流不存在
- `403`: 无权访问（非所有者）

---

#### POST /api/v1/workflows/{workflow_id}/pause

暂停工作流。

**请求体**:

```json
{
  "reason": "需要补充需求细节"
}
```

**响应** (`200`): WorkflowResponse

**错误响应**:
- `404`: 工作流不存在
- `403`: 无权访问
- `400`: 当前状态无法暂停（已完成/已失败）

---

#### POST /api/v1/workflows/{workflow_id}/resume

恢复工作流。

**请求体**:

```json
{
  "user_responses": [
    { "question": "是否需要管理员角色?", "answer": "是" }
  ]
}
```

**响应** (`200`): WorkflowResponse

---

#### GET /api/v1/workflows/{workflow_id}/deliverables

获取工作流交付物。

**响应** (`200`):

```json
{
  "workflow_id": "wf-abc123",
  "prototype_url": "prototype.html",
  "prd_document_url": "prd.md",
  "verification_report": {
    "report_id": "...",
    "prototype_issues": [],
    "document_issues": [],
    "consistency_issues": [],
    "auto_fixed_issues": [],
    "manual_review_required": []
  }
}
```

---

### 组件库模块 (`/api/v1/components`)

所有组件端点需要 JWT 认证。

#### POST /api/v1/components

上传新组件。

**请求体**:

```json
{
  "name": "DataTable",
  "display_name": "数据表格",
  "description": "支持排序、筛选、分页的数据表格组件",
  "category": "data_display",
  "tags": ["table", "data", "pagination"],
  "version": "1.0.0",
  "html_template": "<table>...</table>",
  "css_content": "...",
  "js_content": "...",
  "changelog": "初始版本",
  "props_schema": { "dataSource": { "type": "array" } }
}
```

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| name | string | 是 | 组件名称 |
| display_name | string | 否 | 显示名称 |
| description | string | 否 | 组件描述 |
| category | string | 否 | 分类，枚举值见下方 |
| tags | string[] | 否 | 标签列表 |
| version | string | 否 | 版本号，默认 1.0.0 |
| html_template | string | 否 | HTML 模板 |
| css_content | string | 否 | CSS 内容 |
| js_content | string | 否 | JS 内容 |
| changelog | string | 否 | 变更日志 |
| props_schema | object | 否 | 属性定义 |

**ComponentCategory 枚举值**: `layout`, `form`, `data_display`, `navigation`, `feedback`, `button`, `input`, `custom`

---

#### GET /api/v1/components

搜索组件。

**查询参数**:

| 参数 | 类型 | 说明 |
|-----|------|------|
| q | string | 搜索关键词 |
| category | string | 分类过滤 |
| tag | string | 标签过滤 |
| status | string | 状态过滤 (`draft`, `published`, `deprecated`) |
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 20，最大 100 |

**响应** (`200`):

```json
{
  "components": [ { ... } ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

---

#### GET /api/v1/components/{component_id}

获取组件详情。

**响应** (`200`): 组件信息字典

**错误响应**: `404` - 组件不存在

---

#### DELETE /api/v1/components/{component_id}

删除组件。

**响应** (`200`):

```json
{
  "message": "Component comp-xxx deleted successfully"
}
```

---

### 集成配置模块 (`/api/v1/integrations`)

所有集成端点需要 JWT 认证。

#### POST /api/v1/integrations/configs

创建集成配置。

**请求体**:

```json
{
  "name": "My Jira",
  "integration_type": "jira",
  "enabled": true,
  "api_endpoint": "https://mycompany.atlassian.net",
  "api_key": "...",
  "api_secret": "",
  "access_token": "",
  "settings": { "project_key": "PROJ" }
}
```

**IntegrationType 枚举值**: `jira`, `trello`, `feishu`, `figma`, `sketch`, `github`, `gitlab`, `custom`

**响应** (`200`): 配置信息（不包含密钥）

---

#### GET /api/v1/integrations/configs

列出集成配置。

**查询参数**:

| 参数 | 类型 | 说明 |
|-----|------|------|
| integration_type | string | 集成类型过滤 |
| enabled_only | bool | 仅显示启用的配置 |

---

#### GET /api/v1/integrations/configs/{config_id}

获取集成配置详情（包含 settings）。

---

#### PUT /api/v1/integrations/configs/{config_id}

更新集成配置。

---

#### DELETE /api/v1/integrations/configs/{config_id}

删除集成配置。

---

#### POST /api/v1/integrations/configs/{config_id}/sync-tasks

在集成配置下创建同步任务。

**请求体**:

```json
{
  "direction": "import",
  "workflow_id": "wf-abc123",
  "source_data": { "issue_key": "PROJ-123" }
}
```

**SyncDirection 枚举值**: `import`, `export`, `bidirectional`

**响应** (`200`): 同步任务信息

---

#### GET /api/v1/integrations/sync-tasks

列出同步任务。

**查询参数**: `integration_id`, `workflow_id`, `status`

**SyncStatus 枚举值**: `pending`, `running`, `completed`, `failed`, `cancelled`

---

#### GET /api/v1/integrations/sync-tasks/{task_id}

获取同步任务详情（包含 source_data、result_data）。

---

#### POST /api/v1/integrations/sync-tasks/{task_id}/cancel

取消同步任务。

---

### 健康检查

#### GET /health

**响应** (`200`):

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## 数据库 Schema

### 用户表 (`users`)

| 列名 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | UUID |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | 用户邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 密码哈希 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否激活 |
| created_at | DATETIME | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | 更新时间 |

**SQLAlchemy 模型** (`auth/models.py`):

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## 核心业务模型 (Pydantic)

### WorkflowStatus 枚举

```
init -> parsing -> parsed -> generating -> generated -> verifying -> verified -> completed
                                                      -> failed
parsing -> waiting_user_input -> parsing (循环)
```

### StructuredRequirement

需求解析的结构化输出：

```python
class StructuredRequirement(BaseModel):
    entities: list[BusinessEntity]      # 业务实体
    roles: list[Role]                   # 用户角色
    rules: RuleTreeNode                 # 业务规则树
    flows: list[UserFlow]              # 用户操作流程
    branches: list[Branch]             # 操作分支
    edge_cases: list[EdgeCase]         # 边界场景
    clarifications: list[Question]     # 待澄清问题
    reasoning_trace: str               # 推理路径记录
```

### WorkflowRun

工作流运行记录：

```python
class WorkflowRun(BaseModel):
    id: str                            # 唯一标识 (wf-xxx)
    user_id: str                       # 用户ID
    requirement_text: str              # 原始需求文本
    status: WorkflowStatus             # 当前状态
    created_at: datetime
    updated_at: datetime
    structured_requirement: Optional[StructuredRequirement]
    prototype_url: Optional[str]       # 原型访问URL
    prd_document_url: Optional[str]    # PRD文档URL
    verification_report: Optional[VerificationReport]
    error_message: Optional[str]
```

### VerificationReport

综合校验报告：

```python
class VerificationReport(BaseModel):
    report_id: str
    generated_at: datetime
    requirement_id: str
    prototype_passed: bool
    document_passed: bool
    consistency_passed: bool
    issues: list[CategorizedIssue]
    summary: IssueSummary
    auto_fix_result: Optional[FixResult]
    overall_passed: bool
    summary_text: str
```

### IntegrationConfig

外部系统集成配置：

```python
class IntegrationConfig(BaseModel):
    id: str
    name: str
    integration_type: IntegrationType   # jira, figma, github, ...
    enabled: bool
    api_endpoint: str
    api_key: str                        # 加密存储
    api_secret: str                     # 加密存储
    access_token: str                   # 加密存储
    settings: Optional[dict]
    created_by: str
    created_at: datetime
    updated_at: datetime
```

### SyncTask

数据同步任务：

```python
class SyncTask(BaseModel):
    id: str
    integration_id: str                # 关联的集成配置ID
    workflow_id: str                   # 关联的工作流ID
    direction: SyncDirection           # import, export, bidirectional
    status: SyncStatus                 # pending, running, completed, failed, cancelled
    progress: float                    # 0.0 - 100.0
    source_data: Optional[dict]
    result_data: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

### Component

组件定义：

```python
class Component(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    category: ComponentCategory        # layout, form, data_display, ...
    tags: list[str]
    status: ComponentStatus            # draft, published, deprecated
    current_version: str               # semver
    meta: ComponentMeta
    created_at: datetime
    updated_at: datetime
```
