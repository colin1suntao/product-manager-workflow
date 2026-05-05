# 部署文档

本文档介绍如何部署产品经理多Agent协作工作站。

## 目录

- [环境要求](#环境要求)
- [本地开发](#本地开发)
- [Docker Compose 部署](#docker-compose-部署)
- [Kubernetes 部署](#kubernetes-部署)
- [环境变量配置](#环境变量配置)
- [健康检查](#健康检查)
- [常见问题](#常见问题)

## 环境要求

### 本地开发
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

### Docker 部署
- Docker 20.10+
- Docker Compose 2.0+

### Kubernetes 部署
- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+ (可选)

## 本地开发

### 1. 安装后端依赖

```bash
pip install -e .
```

### 2. 启动后端服务

```bash
uvicorn pm_workstation.api.app:create_app --host 0.0.0.0 --port 8000 --reload
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端服务

```bash
npm run dev
```

### 5. 访问应用

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## Docker Compose 部署

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的 API 密钥
```

### 2. 启动所有服务

```bash
docker compose up -d
```

### 3. 查看服务状态

```bash
docker compose ps
```

### 4. 查看日志

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 5. 停止服务

```bash
docker compose down
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Next.js 应用 |
| 后端 | 8000 | FastAPI 服务 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存/消息队列 |
| MinIO | 9000/9001 | 对象存储/控制台 |

## Kubernetes 部署

### 1. 创建命名空间

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. 配置密钥

```bash
kubectl apply -f k8s/secrets.yaml
```

> 注意：生产环境请使用 `kubectl create secret` 或外部密钥管理工具

### 3. 部署应用

```bash
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
```

### 4. 查看部署状态

```bash
kubectl get all -n pm-workstation
```

### 5. 配置 Ingress

修改 `k8s/frontend.yaml` 中的 Ingress 配置，设置正确的域名。

### 6. 扩缩容

```bash
kubectl scale deployment backend -n pm-workstation --replicas=3
kubectl scale deployment frontend -n pm-workstation --replicas=3
```

## 环境变量配置

### 后端环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `DATABASE_URL` | 是 | PostgreSQL 连接字符串 |
| `REDIS_URL` | 是 | Redis 连接字符串 |
| `MINIO_ENDPOINT` | 是 | MinIO 服务地址 |
| `MINIO_ACCESS_KEY` | 是 | MinIO 访问密钥 |
| `MINIO_SECRET_KEY` | 是 | MinIO 秘密密钥 |
| `OPENAI_API_KEY` | 是 | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | 是 | Anthropic API 密钥 |
| `PORT` | 否 | 服务端口 (默认 8000) |

### 前端环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `NEXT_PUBLIC_API_URL` | 是 | 后端 API 地址 |
| `NODE_ENV` | 否 | 运行环境 (默认 production) |

## 健康检查

### 后端健康检查

```bash
curl http://localhost:8000/health
```

返回示例:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "0.1.0"
}
```

### 数据库连接检查

```bash
curl http://localhost:8000/health/db
```

### Redis 连接检查

```bash
curl http://localhost:8000/health/redis
```

## 常见问题

### 1. 后端启动失败

检查 PostgreSQL 和 Redis 是否正常运行:

```bash
docker compose ps db redis
```

### 2. 前端无法连接后端

检查 `NEXT_PUBLIC_API_URL` 环境变量是否正确配置。

### 3. MinIO 连接失败

检查 MinIO 服务是否启动，以及访问密钥是否正确。

### 4. LLM API 调用失败

检查 `OPENAI_API_KEY` 和 `ANTHROPIC_API_KEY` 是否配置正确。

### 5. 数据库迁移

```bash
alembic upgrade head
```

### 6. 清理 Docker 数据

```bash
docker compose down -v
```

> 注意：这将删除所有持久化数据

## 生产环境建议

1. **密钥管理**: 使用 Kubernetes Secrets、AWS Secrets Manager 或 HashiCorp Vault
2. **数据库备份**: 配置 PostgreSQL 自动备份
3. **监控告警**: 集成 Prometheus + Grafana
4. **日志聚合**: 使用 ELK Stack 或 Loki
5. **HTTPS**: 配置 Ingress TLS 证书
6. **资源限制**: 根据实际负载调整 CPU 和内存限制
7. **自动扩缩容**: 配置 HPA (Horizontal Pod Autoscaler)
