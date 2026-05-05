# 开发者指南

## 环境搭建

### 前置要求

- Python 3.11+
- Node.js 20+（前端开发）
- Docker & Docker Compose（可选，用于完整部署）

### 后端安装

```bash
# 克隆项目后进入目录
cd /workspace

# 安装开发依赖
pip install -e ".[dev]"
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的 API 密钥：

```env
# LLM 配置
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 数据库
DATABASE_URL=sqlite:///./pm_workstation.db

# JWT 认证（生产环境务必更换）
JWT_SECRET_KEY=your-secret-key-change-in-production

# 存储
STORAGE_TYPE=local
STORAGE_PATH=./data/deliverables
```

### 启动后端

```bash
# 方式一：使用 CLI
pm-workstation serve --reload

# 方式二：直接使用 uvicorn
uvicorn pm_workstation.api:create_app --factory --reload --port 8000
```

启动后访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`。

### Docker Compose 完整部署

```bash
docker compose up -d
```

这将启动以下服务：
- **backend**: FastAPI (端口 8000)
- **frontend**: Next.js (端口 3000)
- **db**: PostgreSQL (端口 5432)
- **redis**: Redis (端口 6379)
- **minio**: MinIO (端口 9000 API / 9001 Console)

---

## 运行测试

### 后端测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_auth_api.py

# 运行特定测试函数
pytest tests/unit/test_jwt.py::test_create_access_token

# 运行测试并查看覆盖率
pytest --cov=src --cov-report=html

# 运行测试（详细输出）
pytest -v --tb=short
```

**测试目录结构**:

```
tests/
├── unit/                  # 单元测试
│   ├── test_auth_api.py         # 认证 API 测试
│   ├── test_auth_dependencies.py # 认证依赖测试
│   ├── test_jwt.py              # JWT 工具测试
│   ├── test_user_store.py       # 用户存储测试
│   ├── test_token_store.py      # Token 存储测试
│   ├── test_api.py              # API 路由测试
│   ├── test_orchestrator.py     # 工作流编排测试
│   ├── test_requirement_parser.py # 需求解析测试
│   ├── test_verification.py     # 校验模块测试
│   ├── test_document_verification.py
│   ├── test_verification_fix.py # 自动修复测试
│   ├── test_integrations.py     # 集成模块测试
│   ├── test_integrations_api.py # 集成 API 测试
│   ├── test_component_store.py  # 组件存储测试
│   ├── test_model_router.py     # 模型路由测试
│   ├── test_model_adapters.py   # 模型适配器测试
│   ├── test_structured_output.py
│   ├── test_reasoning_core.py
│   ├── test_document.py         # 文档模块测试
│   ├── test_prototype.py        # 原型模块测试
│   ├── test_models.py           # 数据模型测试
│   ├── test_config.py           # 配置测试
│   ├── test_database_storage.py
│   ├── test_message_queue.py
│   └── test_task_dispatch.py
├── integration/           # 集成测试
├── e2e/                   # 端到端测试
└── performance/           # 性能测试
```

### 前端测试

```bash
cd frontend
npm run test
```

使用 Vitest + Testing Library 运行前端单元测试。

---

## 代码质量工具

### Linting

```bash
# 检查代码
ruff check src tests

# 自动修复可修复的问题
ruff check src tests --fix

# 格式化代码
ruff format src tests
```

### 类型检查

```bash
mypy src
```

### Pre-commit

```bash
# 安装 pre-commit hooks
pre-commit install

# 手动运行所有 hooks
pre-commit run --all-files
```

---

## 添加新功能

### 添加新的 API 端点

1. **在 `api/routes/` 下创建或修改路由文件**:

```python
# api/routes/my_feature.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/my-feature", tags=["我的功能"])

@router.get("")
async def list_items(user_id: str = Depends(get_current_user)):
    return {"items": []}
```

2. **在 `api/app.py` 中注册路由**:

```python
from pm_workstation.api.routes.my_feature import router as my_feature_router

app.include_router(my_feature_router, prefix="/api/v1", tags=["我的功能"])
```

3. **在 `api/schemas.py` 中定义请求/响应模型**（如需要）。

4. **编写测试**:

```python
# tests/unit/test_my_feature.py
import pytest

@pytest.mark.asyncio
async def test_list_items():
    # 测试实现
    pass
```

### 添加新的 LLM 适配器

1. **在 `model_router/` 下创建适配器文件**:

```python
# model_router/mymodel_adapter.py
from pm_workstation.model_router.base import LLMBackend, LLMConfig, LLMMessage, LLMResponse

class MyModelAdapter(LLMBackend):
    def __init__(self, config: LLMConfig):
        super().__init__(config)

    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        # 实现聊天逻辑
        pass

    async def chat_stream(self, messages: list[LLMMessage], **kwargs):
        # 实现流式聊天
        pass

    def get_model_name(self) -> str:
        return "mymodel"

    def is_available(self) -> bool:
        return bool(self.config.api_key)
```

2. **在 `model_router/__init__.py` 中导出**。

3. **在 `model_router/model_selector.py` 中注册**。

### 添加新的外部系统集成

1. **在 `integrations/adapters/` 下创建适配器**:

```python
# integrations/adapters/myservice_adapter.py
from pm_workstation.integrations.adapters.base import BaseAdapter

class MyServiceAdapter(BaseAdapter):
    async def sync_import(self, config, source_data):
        # 实现导入逻辑
        pass

    async def sync_export(self, config, data):
        # 实现导出逻辑
        pass
```

2. **在 `integrations/adapters/registry.py` 中注册**:

```python
from .myservice_adapter import MyServiceAdapter

adapter_registry.register("myservice", MyServiceAdapter)
```

3. **在 `integrations/models.py` 的 `IntegrationType` 枚举中添加**:

```python
class IntegrationType(str, Enum):
    # ...
    MYSERVICE = "myservice"
```

### 添加新的校验检查器

1. **在 `verification/` 下创建检查器**:

```python
# verification/my_checker.py
class MyChecker:
    def check(self, requirement, prototype_structure, document_content):
        issues = []
        # 实现检查逻辑
        return CheckResult(passed=not issues, issues=issues)
```

2. **在 `verification/` 的某个模块中集成**，或在 `IssueReporter` 中汇总结果。

---

## 代码约定

### 命名规范

- **模块/包**: 小写下划线，如 `requirement_parser`
- **类**: PascalCase，如 `RequirementParser`
- **函数/方法**: 小写下划线，如 `parse_requirement`
- **常量**: 大写下划线，如 `MAX_RETRIES`
- **Pydantic 模型**: PascalCase，如 `WorkflowResponse`

### 类型注解

所有函数必须有类型注解：

```python
async def parse(self, requirement_text: str) -> StructuredRequirement:
    """解析需求文本
    
    Args:
        requirement_text: 原始需求文本
        
    Returns:
        结构化需求
    """
    pass
```

### 错误处理

- API 层使用 `HTTPException` 返回标准错误响应
- 业务逻辑层使用自定义异常或 `ValueError`
- 认证失败统一返回 401，权限不足返回 403

### 文档字符串

所有公开 API 和类必须有中文文档字符串，包含 Args 和 Returns 说明。

---

## 调试技巧

### 启用调试模式

```bash
# 在 .env 中设置
DEBUG=true
```

这将：
- 开启 SQLAlchemy 的 SQL 日志
- 开启 uvicorn 的 reload 模式

### IPython 调试

```bash
pip install ipython ipdb
```

在代码中插入断点：

```python
import ipdb; ipdb.set_trace()
```

### 查看覆盖率报告

```bash
pytest --cov=src --cov-report=html
# 打开 htmlcov/index.html 查看
```

---

## 常见问题

### 数据库初始化

当前开发模式使用 SQLite (`pm_auth.db`)，数据库表在 `get_db_session` 依赖中自动创建：

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

生产环境切换到 PostgreSQL 时，需要配置 Alembic 进行数据库迁移。

### TokenStore 生产环境

当前 `TokenStore` 使用内存字典存储撤销的 Token JTI，进程重启会丢失。生产环境应切换为 Redis 实现：

```python
class RedisTokenStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def revoke_token(self, jti: str, expires_at: int) -> None:
        ttl = expires_at - int(time.time())
        await self.redis.setex(f"revoked:{jti}", ttl, "1")

    async def is_revoked(self, jti: str) -> bool:
        return await self.redis.exists(f"revoked:{jti}") is not None
```

### 组件存储生产环境

当前 `InMemoryComponentStore` 使用内存字典，生产环境应使用数据库持久化。
