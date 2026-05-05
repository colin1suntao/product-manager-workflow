# 认证模块 (auth)

## 概述

认证模块提供基于 JWT 的用户认证系统，包括用户注册、登录、Token 刷新、登出和密码修改功能。采用 Access Token + Refresh Token 双 Token 机制，确保 API 安全性。

## 模块结构

```
src/pm_workstation/auth/
├── __init__.py
├── jwt.py              # JWT Token 签发、解码、验证
├── user_store.py       # 用户数据持久化（SQLAlchemy 异步模式）
├── token_store.py      # Token 撤销存储（内存实现）
├── models.py           # SQLAlchemy 用户模型 + Pydantic 请求/响应模型
└── dependencies.py     # FastAPI 认证依赖注入
```

## 核心组件

### JWT 工具 (`jwt.py`)

提供 Token 的创建、解码和验证功能。

#### 函数列表

| 函数 | 说明 | 返回值 |
|-----|------|--------|
| `create_access_token(user_id: str)` | 创建 Access Token（有效期 15 分钟） | `str` |
| `create_refresh_token(user_id: str)` | 创建 Refresh Token（有效期 7 天） | `tuple[str, str]` - (token, jti) |
| `decode_token(token: str, secret?: str)` | 解码 JWT Token | `dict[str, Any]` |
| `verify_access_token(token: str)` | 验证 Access Token（检查类型和有效期） | `dict[str, Any]` |
| `verify_refresh_token(token: str)` | 验证 Refresh Token（检查类型和有效期） | `dict[str, Any]` |

#### Token Payload 结构

**Access Token**:
```json
{
  "sub": "user-uuid",
  "type": "access",
  "iat": 1714900000,
  "exp": 1714900900
}
```

**Refresh Token**:
```json
{
  "sub": "user-uuid",
  "type": "refresh",
  "jti": "uuid-unique-identifier",
  "iat": 1714900000,
  "exp": 1715504800
}
```

| Claim | 说明 |
|-------|------|
| `sub` | 用户唯一标识 |
| `type` | Token 类型（"access" 或 "refresh"） |
| `jti` | JWT ID，仅 Refresh Token 有，用于撤销 |
| `iat` | 签发时间（UTC） |
| `exp` | 过期时间（UTC） |

#### 配置项

Token 配置通过 `config.settings` 读取：

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `jwt_secret_key` | "your-secret-key-change-in-production" | 签名密钥 |
| `jwt_algorithm` | "HS256" | 签名算法 |
| `access_token_expire_minutes` | 15 | Access Token 有效期（分钟） |
| `refresh_token_expire_days` | 7 | Refresh Token 有效期（天） |

---

### UserStore (`user_store.py`)

用户数据的持久化操作，使用 SQLAlchemy 异步模式。

#### 类: `UserStore`

```python
class UserStore:
    def __init__(self, db_session: AsyncSession)
    async def create_user(self, email: str, password: str) -> User
    async def find_by_email(self, email: str) -> Optional[User]
    async def find_by_id(self, user_id: str) -> Optional[User]
    async def update_password(self, user_id: str, new_password: str) -> bool
```

| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `create_user(email, password)` | 创建新用户（自动哈希密码） | `User` 对象 |
| `find_by_email(email)` | 通过邮箱查找用户 | `User` 或 `None` |
| `find_by_id(user_id)` | 通过 ID 查找用户 | `User` 或 `None` |
| `update_password(user_id, new_password)` | 更新用户密码 | `bool` - 是否成功 |

#### 密码哈希

使用 `bcrypt` 算法：

```python
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    pwd_bytes = password.encode("utf-8")[:72]  # bcrypt 限制 72 字节
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
```

---

### TokenStore (`token_store.py`)

Token 撤销存储，实现 Refresh Token 黑名单机制。

#### 类: `TokenStore`

```python
class TokenStore:
    async def revoke_token(self, jti: str, expires_at: int) -> None
    async def is_revoked(self, jti: str) -> bool
    async def cleanup_expired(self) -> int
```

| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `revoke_token(jti, expires_at)` | 撤销 Token（加入黑名单） | `None` |
| `is_revoked(jti)` | 检查 Token 是否已撤销 | `bool` |
| `cleanup_expired()` | 清理过期的撤销记录 | `int` - 清理数量 |

**当前实现**: 使用内存字典 `dict[str, int]` 存储 JTI 到过期时间戳的映射。

**生产环境建议**: 切换为 Redis 实现，使用 `SETEX` 命令自动设置 TTL。

**全局单例**: `token_store = TokenStore()`

---

### 数据模型 (`models.py`)

#### SQLAlchemy 模型

**User** (`users` 表):

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | String(36) | PRIMARY KEY | UUID |
| email | String(255) | UNIQUE, NOT NULL, INDEX | 邮箱 |
| password_hash | String(255) | NOT NULL | bcrypt 哈希 |
| is_active | Boolean | NOT NULL, DEFAULT TRUE | 是否激活 |
| created_at | DateTime | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | DateTime | NOT NULL, DEFAULT NOW(), ON UPDATE | 更新时间 |

#### Pydantic 模型

| 模型 | 用途 | 字段 |
|-----|------|------|
| `UserCreate` | 注册请求 | email (EmailStr), password (8-128 字符) |
| `UserResponse` | 用户响应 | id, email, is_active, created_at, updated_at |
| `TokenPair` | Token 对响应 | access_token, refresh_token, token_type, expires_in |
| `TokenRefresh` | 刷新请求 | refresh_token |
| `PasswordChange` | 改密请求 | old_password, new_password (8-128 字符) |
| `LoginRequest` | 登录请求 | email, password |
| `LogoutRequest` | 登出请求 | refresh_token |

---

### 认证依赖 (`dependencies.py`)

提供 FastAPI 依赖注入，用于路由级别的认证保护。

#### `get_current_user`

强制认证依赖，用于需要登录的端点：

```python
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """
    Returns:
        用户 ID (str)
    Raises:
        HTTPException 401: 未提供 Token / Token 无效 / Token 过期
    """
```

**认证流程**:
1. 从 `Authorization: Bearer <token>` 头提取 Token
2. 验证 Token 类型必须为 "access"
3. 提取 `sub` 字段作为 user_id 返回

#### `get_current_user_optional`

可选认证依赖，用于允许匿名访问的端点：

```python
async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Returns:
        用户 ID 或 None（匿名）
    """
```

使用方式：
```python
@router.get("/public")
async def public_endpoint(user_id: Optional[str] = Depends(get_current_user_optional)):
    if user_id:
        # 已登录用户
        pass
    else:
        # 匿名用户
        pass
```

---

## API 端点

### 注册

```
POST /api/v1/auth/register
```

- 检查邮箱是否已存在
- 创建用户（密码自动哈希）
- 返回 UserResponse（不包含密码）

### 登录

```
POST /api/v1/auth/login
```

- 查找用户
- 验证密码
- 签发 Access Token + Refresh Token
- 返回 TokenPair（expires_in: 900 秒）

### 刷新 Token

```
POST /api/v1/auth/refresh
```

- 验证 Refresh Token 有效性
- 检查是否已被撤销
- 签发新的 Access Token
- 返回新的 Token 对

### 登出

```
POST /api/v1/auth/logout
```

- 验证 Refresh Token
- 提取 JTI 和过期时间
- 将 JTI 加入撤销黑名单
- 登出成功

### 修改密码

```
POST /api/v1/auth/password
```

- 验证旧密码
- 更新为新密码（自动哈希）
- 撤销所有已签发的 Refresh Token（简化实现）
- 改密成功

---

## 安全注意事项

1. **JWT_SECRET_KEY**: 生产环境必须更换默认密钥
2. **密码长度**: 限制 72 字节（bcrypt 限制），前端应在 72 字符处截断
3. **Token 撤销**: 当前为内存实现，重启丢失，生产应使用 Redis
4. **改密撤销**: 修改密码时简化实现为撤销所有 Token，生产可基于用户 ID 批量撤销
5. **HTTPS**: 生产环境必须使用 HTTPS 传输 Token
6. **CORS**: 配置允许的前端域名

---

## 测试文件

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/unit/test_jwt.py` | Token 创建、验证、过期、类型检查 |
| `tests/unit/test_user_store.py` | 用户 CRUD、密码哈希/验证 |
| `tests/unit/test_token_store.py` | Token 撤销、过期清理 |
| `tests/unit/test_auth_api.py` | 注册、登录、刷新、登出、改密 API |
| `tests/unit/test_auth_dependencies.py` | get_current_user 依赖行为 |
