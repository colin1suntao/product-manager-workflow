# 外部系统集成模块 (integrations)

## 概述

集成模块提供与外部项目管理、设计工具和代码管理平台的对接能力，支持配置管理和数据双向同步。采用适配器模式实现多系统支持。

## 模块结构

```
src/pm_workstation/integrations/
├── __init__.py
├── models.py              # 集成配置和同步任务模型
├── store.py               # 内存存储实现
└── adapters/              # 外部系统适配器
    ├── __init__.py
    ├── base.py            # 适配器抽象基类
    ├── jira_adapter.py    # Jira 适配器
    ├── trello_adapter.py  # Trello 适配器
    ├── feishu_adapter.py  # 飞书适配器
    ├── figma_adapter.py   # Figma 适配器
    ├── sketch_adapter.py  # Sketch 适配器
    ├── github_adapter.py  # GitHub 适配器
    ├── gitlab_adapter.py  # GitLab 适配器
    └── registry.py        # 适配器注册表
```

## 数据模型 (`models.py`)

### IntegrationType 枚举

支持的外部系统类型：

| 枚举值 | 说明 |
|-------|------|
| `jira` | Atlassian Jira（项目管理和 issue 跟踪） |
| `trello` | Trello（看板管理） |
| `feishu` | 飞书（协作平台） |
| `figma` | Figma（设计工具） |
| `sketch` | Sketch（设计工具） |
| `github` | GitHub（代码托管） |
| `gitlab` | GitLab（代码托管） |
| `custom` | 自定义系统 |

### SyncDirection 枚举

| 枚举值 | 说明 |
|-------|------|
| `import` | 从外部系统导入数据 |
| `export` | 导出数据到外部系统 |
| `bidirectional` | 双向同步 |

### SyncStatus 枚举

| 枚举值 | 说明 |
|-------|------|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

### IntegrationConfig

集成配置模型：

```python
class IntegrationConfig(BaseModel):
    id: str                           # 配置唯一标识 (int-xxx)
    name: str                         # 配置名称
    integration_type: IntegrationType # 集成类型
    enabled: bool = True              # 是否启用
    api_endpoint: str = ""            # API 端点
    api_key: str = ""                 # API 密钥（应加密存储）
    api_secret: str = ""              # API 密钥（应加密存储）
    access_token: str = ""            # 访问令牌（应加密存储）
    settings: Optional[dict] = None   # 额外配置
    created_by: str = ""              # 创建者
    created_at: datetime              # 创建时间
    updated_at: datetime              # 更新时间
```

### SyncTask

同步任务模型：

```python
class SyncTask(BaseModel):
    id: str                           # 任务唯一标识 (sync-xxx)
    integration_id: str               # 关联的集成配置ID
    workflow_id: str = ""             # 关联的工作流ID
    direction: SyncDirection          # 同步方向
    status: SyncStatus                # 同步状态
    progress: float                   # 进度百分比 (0.0-100.0)
    source_data: Optional[dict]       # 源数据信息
    result_data: Optional[dict]       # 同步结果
    error_message: Optional[str]      # 错误信息
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

**状态转换方法**:
- `start()`: pending -> running
- `complete(result_data)`: running -> completed
- `fail(error_message)`: running -> failed
- `cancel()`: pending/running -> cancelled

---

## 存储层 (`store.py`)

### IntegrationStore

集成配置的内存存储：

```python
class IntegrationStore:
    def create_config(self, config: IntegrationConfig) -> IntegrationConfig
    def get_config(self, config_id: str) -> Optional[IntegrationConfig]
    def update_config(self, config_id: str, **kwargs) -> Optional[IntegrationConfig]
    def delete_config(self, config_id: str) -> bool
    def list_configs(
        self,
        integration_type: Optional[IntegrationType] = None,
        enabled_only: bool = False,
    ) -> list[IntegrationConfig]
```

### SyncTaskStore

同步任务的内存存储：

```python
class SyncTaskStore:
    def create_task(self, task: SyncTask) -> SyncTask
    def get_task(self, task_id: str) -> Optional[SyncTask]
    def update_task(self, task_id: str, **kwargs) -> Optional[SyncTask]
    def list_tasks(
        self,
        integration_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        status: Optional[SyncStatus] = None,
    ) -> list[SyncTask]
    def cancel_task(self, task_id: str) -> bool
```

**全局实例**:
```python
integration_store = IntegrationStore()
sync_task_store = SyncTaskStore()
```

---

## 适配器模式 (`adapters/`)

### 基类 (`base.py`)

所有适配器继承自统一的抽象基类，定义标准的同步接口：

```python
# adapters/base.py
class BaseAdapter:
    async def sync_import(self, config: IntegrationConfig, source_data: dict) -> dict:
        """从外部系统导入数据"""
        pass
    
    async def sync_export(self, config: IntegrationConfig, data: dict) -> dict:
        """导出数据到外部系统"""
        pass
    
    async def test_connection(self, config: IntegrationConfig) -> bool:
        """测试连接是否可用"""
        pass
```

### 已实现的适配器

| 适配器 | 文件 | 说明 |
|-------|------|------|
| JiraAdapter | `jira_adapter.py` | Jira issue 导入/导出 |
| TrelloAdapter | `trello_adapter.py` | Trello 看板同步 |
| FeishuAdapter | `feishu_adapter.py` | 飞书文档/任务集成 |
| FigmaAdapter | `figma_adapter.py` | Figma 设计稿同步 |
| SketchAdapter | `sketch_adapter.py` | Sketch 文件处理 |
| GitHubAdapter | `github_adapter.py` | GitHub issue/PR 同步 |
| GitLabAdapter | `gitlab_adapter.py` | GitLab issue/MR 同步 |

### 适配器注册表 (`registry.py`)

```python
# adapters/registry.py
adapter_registry = {}

def register(name: str, adapter_class: type):
    adapter_registry[name] = adapter_class

def get_adapter(name: str) -> BaseAdapter:
    return adapter_registry[name]()
```

---

## API 端点

详见 [API 接口文档](../INTERFACES.md#集成配置模块-apiv1integrations)。

### 配置管理

```
POST   /api/v1/integrations/configs           # 创建配置
GET    /api/v1/integrations/configs           # 列出配置
GET    /api/v1/integrations/configs/{id}      # 获取详情
PUT    /api/v1/integrations/configs/{id}      # 更新配置
DELETE /api/v1/integrations/configs/{id}      # 删除配置
```

### 同步任务

```
POST   /api/v1/integrations/configs/{id}/sync-tasks    # 创建任务
GET    /api/v1/integrations/sync-tasks                 # 列出任务
GET    /api/v1/integrations/sync-tasks/{id}            # 获取详情
POST   /api/v1/integrations/sync-tasks/{id}/cancel     # 取消任务
```

---

## 配置示例

### 创建 Jira 集成

```json
POST /api/v1/integrations/configs
{
  "name": "My Jira Project",
  "integration_type": "jira",
  "enabled": true,
  "api_endpoint": "https://mycompany.atlassian.net/rest/api/3",
  "api_key": "user@example.com",
  "api_secret": "api-token",
  "access_token": "",
  "settings": {
    "project_key": "PM",
    "issue_type": "Story"
  }
}
```

### 创建同步任务

```json
POST /api/v1/integrations/configs/{config_id}/sync-tasks
{
  "direction": "import",
  "workflow_id": "wf-abc123",
  "source_data": {
    "jql": "project = PM AND status = 'To Do'"
  }
}
```

---

## 安全注意事项

1. **密钥存储**: `api_key`, `api_secret`, `access_token` 在生产环境应加密存储
2. **API 端点**: 建议使用 HTTPS 端点
3. **权限控制**: 所有集成 API 端点需要 JWT 认证，配置归属创建者

---

## 生产环境改进建议

1. **持久化存储**: 将 `IntegrationStore` 和 `SyncTaskStore` 从内存切换到数据库
2. **异步任务执行**: 同步任务应使用 Celery 或 RQ 异步执行
3. **加密**: 使用 AES 或 KMS 加密存储 API 密钥
4. **连接池**: 为外部 API 调用实现连接池和重试机制
5. **Webhook**: 支持外部系统的 Webhook 回调

---

## 测试文件

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/unit/test_integrations.py` | 集成配置模型、存储操作 |
| `tests/unit/test_integrations_api.py` | 集成配置 API 端点测试 |
