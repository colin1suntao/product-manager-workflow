# Requirements Document

## Introduction

为产品经理多Agent协作工作站添加 JWT (JSON Web Token) 认证机制，替换当前的 `X-User-ID` 请求头临时认证方案。实现用户注册、登录、Token 签发与验证，确保 API 访问的安全性和用户数据的隔离。

## Glossary

- **JWT (JSON Web Token)**: 用于在客户端和服务端之间安全传递声明的令牌格式
- **Access Token**: 短期有效的 JWT 令牌，用于 API 请求认证
- **Refresh Token**: 长期有效的令牌，用于获取新的 Access Token
- **Password Hash**: 使用 bcrypt 算法对密码进行单向加密存储
- **API Key**: 可选的程序化访问密钥，用于第三方工具集成

## Requirements

### Requirement 1: 用户注册

**User Story:** AS 新用户，I want 通过邮箱和密码创建账户，so that 我可以使用工作站的完整功能。

#### Acceptance Criteria

1. WHEN 用户提交有效的邮箱和密码，系统 SHALL 创建用户账户并返回成功响应
2. WHEN 用户提交的邮箱已被注册，系统 SHALL 返回错误提示 "邮箱已被注册"
3. WHEN 用户提交的密码长度少于8个字符，系统 SHALL 返回错误提示 "密码长度不得少于8个字符"
4. WHEN 用户提交的邮箱格式无效，系统 SHALL 返回错误提示 "邮箱格式无效"
5. WHEN 用户注册成功，系统 SHALL 对密码进行 bcrypt 哈希存储，不保存明文

### Requirement 2: 用户登录

**User Story:** AS 已注册用户，I want 通过邮箱和密码登录，so that 我获得访问 API 的认证令牌。

#### Acceptance Criteria

1. WHEN 用户提供正确的邮箱和密码，系统 SHALL 签发 JWT Access Token 和 Refresh Token 并返回
2. WHEN 用户提供错误的邮箱或密码，系统 SHALL 返回错误提示 "邮箱或密码错误"
3. WHEN 用户登录成功，系统 SHALL 返回包含 Access Token、Refresh Token 和 Token 过期时间的响应
4. WHILE Access Token 有效，用户 SHALL 使用该 Token 访问所有受保护的 API

### Requirement 3: Token 验证

**User Story:** AS 系统，I want 验证每个 API 请求中的 JWT Token，so that 仅允许合法用户访问受保护的资源。

#### Acceptance Criteria

1. WHEN 请求携带有效的 Bearer Token，系统 SHALL 提取 Token 中的用户ID并允许访问
2. WHEN 请求未携带 Token，系统 SHALL 返回 HTTP 401 状态码
3. WHEN 请求携带过期或无效的 Token，系统 SHALL 返回 HTTP 401 状态码和错误信息
4. WHEN Token 被篡改或签名不匹配，系统 SHALL 拒绝请求并返回 HTTP 401

### Requirement 4: Token 刷新

**User Story:** AS 已登录用户，I want 使用 Refresh Token 获取新的 Access Token，so that 我在 Access Token 过期后无需重新登录。

#### Acceptance Criteria

1. WHEN 用户提供有效的 Refresh Token，系统 SHALL 签发新的 Access Token 并返回
2. WHEN 用户提供过期或无效的 Refresh Token，系统 SHALL 返回 HTTP 401
3. WHEN Refresh Token 被使用过，系统 SHALL 拒绝该 Token 并返回错误

### Requirement 5: 用户登出

**User Story:** AS 已登录用户，I want 登出账户，so that 我的 Token 失效，保护账户安全。

#### Acceptance Criteria

1. WHEN 用户请求登出，系统 SHALL 使当前 Refresh Token 失效
2. WHEN 用户登出后尝试使用旧 Token，系统 SHALL 拒绝请求

### Requirement 6: 密码修改

**User Story:** AS 已登录用户，I want 修改我的密码，so that 我可以定期更新密码保证安全。

#### Acceptance Criteria

1. WHEN 用户提供正确的旧密码和符合规则的新密码，系统 SHALL 更新密码哈希
2. WHEN 用户提供的旧密码不正确，系统 SHALL 返回错误提示
3. WHEN 密码修改成功，系统 SHALL 使所有已签发的 Refresh Token 失效
