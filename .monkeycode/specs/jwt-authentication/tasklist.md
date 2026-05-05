# JWT Authentication - Implementation Task List

## Task 1: 添加依赖和配置
- [x] 1.1 在 `pyproject.toml` 中添加 `python-jose[cryptography]`、`passlib[bcrypt]`、`PyJWT` 依赖
- [x] 1.2 在 `src/pm_workstation/config.py` 中添加 JWT 配置项（JWT_SECRET_KEY、JWT_ALGORITHM、ACCESS_TOKEN_EXPIRE_MINUTES、REFRESH_TOKEN_EXPIRE_DAYS）
- [x] 1.3 执行 `pip install` 安装新依赖

## Task 2: 实现 JWT 工具模块
- [x] 2.1 创建 `src/pm_workstation/auth/__init__.py`
- [x] 2.2 创建 `src/pm_workstation/auth/jwt.py`，实现 `create_access_token`、`create_refresh_token`、`decode_token` 函数
- [x] 2.3 为 JWT 工具模块编写单元测试

## Task 3: 实现用户模型和用户存储
- [x] 3.1 创建 `src/pm_workstation/auth/models.py`，定义 SQLAlchemy User 模型和 Pydantic 请求/响应模型
- [x] 3.2 创建 `src/pm_workstation/auth/user_store.py`，实现 UserStore 类（create_user、find_by_email、find_by_id、update_password）
- [x] 3.3 为 UserStore 编写单元测试

## Task 4: 实现 Token 撤销存储
- [x] 4.1 创建 `src/pm_workstation/auth/token_store.py`，使用 Redis 实现 TokenStore（revoke_token、is_revoked）
- [x] 4.2 为 TokenStore 编写单元测试

## Task 5: 实现 Auth 依赖注入
- [x] 5.1 创建 `src/pm_workstation/auth/dependencies.py`，实现 `get_current_user` 依赖（替换现有的 `api/dependencies.py` 中的版本）
- [x] 5.2 为 Auth 依赖编写单元测试

## Task 6: 实现 Auth API 路由
- [x] 6.1 创建 `src/pm_workstation/api/routes/auth.py`，实现 5 个端点（register、login、refresh、logout、password）
- [x] 6.2 在 `src/pm_workstation/api/app.py` 中注册 auth router
- [x] 6.3 修改 `src/pm_workstation/api/dependencies.py`，添加 `get_db_session` 依赖
- [x] 6.4 为 Auth API 路由编写单元测试

## Task 7: 更新现有 API 路由使用新的认证
- [x] 7.1 更新 `src/pm_workstation/api/routes/workflows.py` 使用新的 `get_current_user`
- [x] 7.2 更新 `src/pm_workstation/api/routes/components.py` 使用新的 `get_current_user`
- [x] 7.3 更新 `src/pm_workstation/api/routes/integrations.py` 使用新的 `get_current_user`
- [x] 7.4 运行全量测试确保无回归

## Task 8: 前端 Token 管理和登录页面
- [x] 8.1 创建 `frontend/src/lib/auth.ts`，实现 Token 管理函数
- [x] 8.2 修改 `frontend/src/lib/api.ts`，使用 Bearer Token 替换硬编码 X-User-ID
- [x] 8.3 创建 `frontend/src/app/auth/login/page.tsx` 登录/注册页面
- [x] 8.4 运行前端测试

## Task 9: 端到端集成测试
- [x] 9.1 编写端到端认证流程测试（注册->登录->API访问->刷新->登出）
- [x] 9.2 运行全量测试套件
