# API 路由模块 (api)

## 概述

API 层基于 FastAPI 构建，提供 RESTful 接口供前端调用。所有业务 API 均挂载在 `/api/v1` 前缀下，通过路由组按功能模块组织。

## 应用结构

```
src/pm_workstation/api/
├── __init__.py              # 导出 create_app
├── app.py                   # 应用工厂和生命周期管理
├── dependencies.py          # FastAPI 全局依赖
├── schemas.py               # API 请求/响应 Pydantic 模型
└── routes/
    ├── auth.py              # 认证路由 (已独立模块文档)
    ├── workflows.py         # 工作流管理路由
    ├── components.py        # 组件库路由
    └── integrations.py      # 集成配置路由
```

## 应用工厂 (`app.py`)

### `create_app()`

创建并配置 FastAPI 应用实例：

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="PM Workstation API",
        description="产品经理多Agent协作工作站 API",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # 注册路由
    app.include_router(auth_router, prefix="/api/v1", tags=["认证"])
    app.include_router(workflows_router, prefix="/api/v1", tags=["工作流"])
    app.include_router(components_router, prefix="/api/v1", tags=["组件库"])
    app.include_router(integrations_router, prefix="/api/v1", tags=["集成配置"])
    
    # 健康检查
    @app.get("/health", tags=["健康检查"])
    async def health_check() -> dict:
        return {"status": "ok", "version": "0.1.0"}
    
    return app
```

### 生命周期管理 (`lifespan`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 启动时初始化
    app.state.workflow_manager = WorkflowManager()
    yield
    # 关闭时清理
    pass
```

`WorkflowManager` 实例存储在 `app.state` 中，通过依赖注入在各路由间共享。

---

## 依赖注入 (`dependencies.py`)

### `get_workflow_manager`

从 `app.state` 获取工作流管理器实例：

```python
def get_workflow_manager(request: Request) -> WorkflowManager:
    return request.app.state.workflow_manager
```

### `get_db_session`

获取数据库会话（异步模式）：

```python
async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # 使用 SQLite 异步驱动
    engine = create_async_engine("sqlite+aiosqlite:///./pm_auth.db", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
```

**注意**: 当前为临时实现，使用 SQLite。生产环境应切换为 PostgreSQL 连接池。

### `get_current_user` (API 层)

从请求头 `X-User-ID` 获取用户 ID（临时方案）：

```python
async def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> str:
    if not x_user_id:
        return "anonymous-test-user"
    return x_user_id
```

**注意**: 此为测试用临时方案。生产环境应使用 `auth/dependencies.py` 中的 JWT 验证版本。

---

## 路由组

### 工作流路由 (`routes/workflows.py`)

路由前缀: `/api/v1/workflows`

所有端点需要 JWT 认证（`user_id: str = Depends(get_current_user)`）。

| 方法 | 路径 | 处理函数 | 说明 |
|-----|------|---------|------|
| POST | `/workflows` | `start_workflow` | 启动新工作流 |
| GET | `/workflows` | `list_workflows` | 列出用户的工作流 |
| GET | `/workflows/{id}` | `get_workflow_status` | 查询工作流状态 |
| POST | `/workflows/{id}/pause` | `pause_workflow` | 暂停工作流 |
| POST | `/workflows/{id}/resume` | `resume_workflow` | 恢复工作流 |
| GET | `/workflows/{id}/deliverables` | `get_deliverables` | 获取交付物 |

#### 权限控制

工作流查询/操作时验证用户所有权：

```python
if run.user_id != user_id:
    raise HTTPException(status_code=403, detail="Access denied")
```

#### 响应转换

内部使用 `WorkflowRun` 模型，API 响应使用 `WorkflowResponse`：

```python
def _convert_run_to_response(run) -> WorkflowResponse:
    return WorkflowResponse(
        id=run.id,
        user_id=run.user_id,
        requirement_text=run.requirement_text,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        structured_requirement=run.structured_requirement.model_dump() if run.structured_requirement else None,
        prototype_url=run.prototype_url,
        prd_document_url=run.prd_document_url,
        error_message=run.error_message,
    )
```

---

### 组件库路由 (`routes/components.py`)

路由前缀: `/api/v1/components`

所有端点需要 JWT 认证。

| 方法 | 路径 | 处理函数 | 说明 |
|-----|------|---------|------|
| POST | `/components` | `upload_component` | 上传新组件 |
| GET | `/components` | `search_components` | 搜索组件（支持分页） |
| GET | `/components/{id}` | `get_component` | 获取组件详情 |
| DELETE | `/components/{id}` | `delete_component` | 删除组件 |

#### 存储

当前使用 `InMemoryComponentStore` 内存存储：

```python
_component_store = InMemoryComponentStore()
```

生产环境应切换为数据库持久化。

#### 搜索

支持多维度搜索：
- 关键词 (`q`)
- 分类 (`category`)
- 标签 (`tag`)
- 状态 (`status`)
- 分页 (`page`, `page_size`)

---

### 集成配置路由 (`routes/integrations.py`)

路由前缀: `/api/v1/integrations`

所有端点需要 JWT 认证。

| 方法 | 路径 | 处理函数 | 说明 |
|-----|------|---------|------|
| POST | `/integrations/configs` | `create_integration_config` | 创建集成配置 |
| GET | `/integrations/configs` | `list_integration_configs` | 列出集成配置 |
| GET | `/integrations/configs/{id}` | `get_integration_config` | 获取配置详情 |
| PUT | `/integrations/configs/{id}` | `update_integration_config` | 更新配置 |
| DELETE | `/integrations/configs/{id}` | `delete_integration_config` | 删除配置 |
| POST | `/integrations/configs/{id}/sync-tasks` | `create_sync_task` | 创建同步任务 |
| GET | `/integrations/sync-tasks` | `list_sync_tasks` | 列出同步任务 |
| GET | `/integrations/sync-tasks/{id}` | `get_sync_task` | 获取任务详情 |
| POST | `/integrations/sync-tasks/{id}/cancel` | `cancel_sync_task` | 取消任务 |

#### 存储

使用全局内存存储实例：

```python
from pm_workstation.integrations.store import integration_store, sync_task_store
```

---

## API Schema 模型 (`schemas.py`)

| 模型 | 用途 | 字段 |
|-----|------|------|
| `StartWorkflowRequest` | 启动工作流请求 | requirement_text (string, min 1) |
| `WorkflowResponse` | 工作流响应 | id, user_id, requirement_text, status, created_at, updated_at, structured_requirement, prototype_url, prd_document_url, error_message |
| `WorkflowListResponse` | 工作流列表 | workflows (list), total (int) |
| `PauseWorkflowRequest` | 暂停请求 | reason (optional string) |
| `ResumeWorkflowRequest` | 恢复请求 | user_responses (optional list[dict]) |
| `DeliverablesResponse` | 交付物响应 | workflow_id, prototype_url, prd_document_url, verification_report |
| `ErrorResponse` | 错误响应 | detail (string), code (optional string) |

---

## 错误处理

FastAPI 自动处理以下情况：

| HTTP 状态码 | 场景 |
|------------|------|
| 400 | 请求参数验证失败 |
| 401 | 未认证（JWT 无效或缺失） |
| 403 | 无权访问（非资源所有者） |
| 404 | 资源不存在 |
| 422 | 请求体格式错误（Pydantic 验证失败） |
| 500 | 服务器内部错误 |

---

## 测试文件

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/unit/test_api.py` | 通用 API 路由测试 |
| `tests/unit/test_auth_api.py` | 认证 API 端点测试 |
| `tests/unit/test_integrations_api.py` | 集成配置 API 测试 |
| `tests/unit/test_auth_dependencies.py` | 认证依赖注入测试 |
