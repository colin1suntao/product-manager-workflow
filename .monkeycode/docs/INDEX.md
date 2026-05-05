# 项目文档索引

## 项目概览

**产品经理多Agent协作工作站**（PM Workstation）是一个基于 Python + FastAPI 后端与 Next.js 前端的智能系统，利用 LangChain/LangGraph 框架实现 AI 驱动的需求解析、原型生成、文档编撰和校验纠错。

### 核心功能

| 功能模块 | 说明 |
|---------|------|
| 需求解析 | 依托 LLM 长链推理能力，从碎片化需求文本中提取业务实体、用户角色、操作流程、业务规则树、边界场景等结构化信息 |
| 原型生成 | 根据结构化需求自动生成 HTML/CSS/JS 可交互原型，包含页面结构树、组件匹配和交互配置 |
| 文档编撰 | 自动生成标准化 PRD 文档，支持 Markdown 格式化、模板引擎和术语一致性检查 |
| 校验纠错 | 双向核验原型和文档，检查页面覆盖率、交互逻辑完整性、格式规范性、一致性问题，并支持自动修复 |
| 多模型路由 | 支持 OpenAI、Anthropic 等多种 LLM，具备模型选择、成本优化和故障降级能力 |
| 外部集成 | 支持 Jira、Figma、GitHub、GitLab、飞书、Trello、Sketch 等外部系统的配置和数据同步 |
| JWT 认证 | 用户注册、登录、Token 刷新、登出和密码修改，基于 python-jose 和 bcrypt 实现 |

### 技术栈

| 层级 | 技术 |
|-----|------|
| 后端 | Python 3.11+, FastAPI, LangChain 0.3+, LangGraph 0.2+ |
| 前端 | Next.js 16, React 19, TypeScript, TailwindCSS 4 |
| 数据库 | SQLite (开发), PostgreSQL (生产), SQLAlchemy 2.0+ |
| 缓存 | Redis 7 |
| 存储 | 本地文件系统, MinIO/S3 |
| 认证 | python-jose (JWT), passlib+bcrypt (密码哈希) |
| LLM | OpenAI API, Anthropic API |
| 测试 | pytest, pytest-asyncio, pytest-cov (后端); Vitest, Testing Library (前端) |
| 代码质量 | ruff (lint/format), mypy (类型检查) |

## 文档导航

### 核心文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| 系统架构 | [ARCHITECTURE.md](./ARCHITECTURE.md) | 整体架构设计、分层模型、数据流、JWT 认证架构 |
| API 接口 | [INTERFACES.md](./INTERFACES.md) | REST API 接口定义、请求/响应模型、数据库 Schema |
| 开发指南 | [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | 环境搭建、运行测试、添加功能、代码规范 |

### 模块文档

| 模块 | 路径 | 说明 |
|-----|------|------|
| 认证模块 | [模块/auth.md](./模块/auth.md) | JWT Token 签发/验证、UserStore、TokenStore、认证依赖注入 |
| API 路由 | [模块/api.md](./模块/api.md) | 工作流、组件库、集成配置、认证四大路由组 |
| 工作流编排器 | [模块/orchestrator.md](./模块/orchestrator.md) | LangGraph 状态机、工作流管理、状态定义 |
| 外部集成 | [模块/integrations.md](./模块/integrations.md) | 集成适配器模式、配置存储、同步任务管理 |
| 校验模块 | [模块/verification.md](./模块/verification.md) | 原型校验、文档校验、一致性检查、自动修复、问题报告 |

## 项目结构

```
/workspace
├── src/pm_workstation/          # Python 后端源码
│   ├── api/                     # FastAPI 应用和路由
│   │   ├── app.py               # 应用工厂和生命周期管理
│   │   ├── dependencies.py      # FastAPI 依赖注入
│   │   ├── schemas.py           # API 请求/响应模型
│   │   └── routes/              # 路由处理器
│   │       ├── auth.py          # 认证路由
│   │       ├── workflows.py     # 工作流路由
│   │       ├── components.py    # 组件库路由
│   │       └── integrations.py  # 集成配置路由
│   ├── auth/                    # JWT 认证模块
│   │   ├── jwt.py               # Token 签发/验证
│   │   ├── user_store.py        # 用户数据持久化
│   │   ├── token_store.py       # Token 撤销存储
│   │   ├── models.py            # 用户模型和 Pydantic 模型
│   │   └── dependencies.py      # 认证依赖
│   ├── agents/                  # 需求解析 Agent 子模块
│   │   ├── requirement_parser.py # 主解析器
│   │   ├── branch_analyzer.py   # 分支分析
│   │   ├── clarification_generator.py
│   │   ├── entity_extractor.py
│   │   ├── gap_detector.py
│   │   ├── reasoning_tracer.py
│   │   ├── role_identifier.py
│   │   └── rule_decomposer.py
│   ├── orchestrator/            # 工作流编排
│   │   ├── workflow_graph.py    # LangGraph 图定义
│   │   ├── workflow_manager.py  # 工作流管理器
│   │   └── workflow_state.py    # 工作流状态
│   ├── models/                  # 数据模型
│   │   ├── core.py              # 核心业务模型
│   │   ├── component.py         # 组件库模型
│   │   ├── database.py          # 数据库配置
│   │   └── orm.py               # ORM 基类
│   ├── verification/            # 校验模块
│   │   ├── prototype_verifier.py # 原型校验
│   │   ├── document_verifier.py # 文档校验
│   │   ├── consistency_checker.py # 一致性检查
│   │   ├── autofixer.py         # 自动修复
│   │   ├── issue_reporter.py    # 问题报告
│   │   ├── verification_models.py
│   │   └── document_models.py
│   ├── prototype/               # 原型生成
│   │   ├── page_structure.py    # 页面结构生成
│   │   ├── component_matcher.py # 组件匹配
│   │   ├── html_generator.py    # HTML 生成
│   │   ├── interaction_configurator.py
│   │   └── style_checker.py
│   ├── document/                # 文档生成
│   │   ├── content_generator.py
│   │   ├── markdown_formatter.py
│   │   ├── structure_generator.py
│   │   ├── template_engine.py
│   │   └── terminology_checker.py
│   ├── integrations/            # 外部系统集成
│   │   ├── models.py            # 集成配置模型
│   │   ├── store.py             # 配置和任务存储
│   │   └── adapters/            # 适配器实现
│   │       ├── base.py
│   │       ├── jira_adapter.py
│   │       ├── figma_adapter.py
│   │       ├── github_adapter.py
│   │       ├── gitlab_adapter.py
│   │       ├── feishu_adapter.py
│   │       ├── trello_adapter.py
│   │       ├── sketch_adapter.py
│   │       └── registry.py
│   ├── model_router/            # LLM 模型路由
│   │   ├── base.py              # 抽象基类
│   │   ├── openai_adapter.py
│   │   ├── anthropic_adapter.py
│   │   ├── fallback_handler.py
│   │   ├── model_selector.py
│   │   ├── cost_optimizer.py
│   │   └── task_classifier.py
│   ├── storage/                 # 存储层
│   │   ├── base.py              # 存储接口
│   │   ├── local.py             # 本地存储
│   │   ├── minio.py             # MinIO/S3 存储
│   │   ├── factory.py           # 存储工厂
│   │   ├── component_store.py
│   │   ├── component_store_memory.py
│   │   ├── message_queue.py
│   │   ├── parallel_coordinator.py
│   │   ├── redis_config.py
│   │   └── task_dispatcher.py
│   ├── config.py                # 应用配置 (pydantic-settings)
│   └── cli.py                   # CLI 入口
├── frontend/                    # Next.js 前端
│   ├── src/
│   │   ├── app/                 # App Router 页面
│   │   │   ├── workflows/
│   │   │   ├── requirements/
│   │   │   ├── prototypes/
│   │   │   ├── documents/
│   │   │   ├── integrations/
│   │   │   ├── reports/
│   │   │   └── components-lib/
│   │   ├── components/          # React 组件
│   │   ├── lib/                 # 工具库
│   │   ├── tests/               # 前端测试
│   │   └── types/               # TypeScript 类型
│   ├── next.config.ts
│   ├── package.json
│   └── tsconfig.json
├── tests/                       # 后端测试
│   ├── unit/                    # 单元测试 (27 个测试文件)
│   ├── integration/             # 集成测试
│   ├── e2e/                     # 端到端测试
│   └── performance/             # 性能测试
├── docker-compose.yml           # Docker Compose 配置
├── Dockerfile                   # 后端 Docker 镜像
├── pyproject.toml               # Python 项目配置
└── .env.example                 # 环境变量模板
```
