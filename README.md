# 产品经理多Agent协作工作站

基于Python + LangChain的多Agent协作系统，集需求解析、原型绘制、文档编撰、市场调研、校验纠错于一体，支持聊天式交互和长期记忆。

## 功能特性

### 核心Agent能力
- **需求解析Agent**: 依托长链推理能力，精准解析碎片化业务需求
- **原型Agent**: 自动生成HTML/CSS/JS可交互原型（支持花束设计技能）
- **文档Agent**: 自动编撰标准化PRD文档
- **校验Agent**: 双向核验原型和文档，修复逻辑漏洞
- **市场调研Agent**: 基于PM Skills自动生成市场调研报告

### 交互与记忆
- **聊天式交互**: 支持通过对话与Agent协作，自动识别任务意图并分发
- **模型切换**: 每次对话可指定不同的 LLM 供应商和模型
- **思考过程展示**: AI 思考步骤时间线（意图分析、任务路由、执行链路）
- **上下文管理**: 上下文长度指示器 + 一键压缩（保留最近20条消息）
- **长期记忆系统**: Agent具备Soul人格、偏好记忆、经验学习、反思能力
- **多任务模式**: 需求分析、原型生成、PRD编写、市场调研

### PM Skills技能系统
- **47+ 个专业技能**: 涵盖市场分析、用户研究、产品规划、文档撰写等领域
- **技能导入**: 支持粘贴 SKILL.md 内容或上传 .md 文件导入自定义技能
- **新建技能**: 通过表单直接创建自定义技能（含名称、类型、System Prompt、执行步骤等）
- **技能筛选**: 按类型（组件/交互/工作流）筛选和搜索
- **智能推荐**: 根据需求自动推荐相关技能

### 知识库
- **产品文档模板**: 管理 PRD、敏捷需求等文档模板，支持 CRUD
- **AI 会话集成**: 聊天时选择模板，内容注入 AI 上下文作为 system prompt

### 组件库
- **原型组件模板**: 管理网页/移动端原型模板，独立于文档模板
- **AI 会话集成**: 聊天时选择组件模板，指导 AI 生成对应风格的原型

### 渠道接入
- **飞书机器人**: 支持 tenant_access_token 认证、HMAC 签名验证、消息解析与回复
- **企业微信机器人**: 支持 access_token 认证、XML 消息解析、单聊/群聊回复
- **AI 集成**: 渠道消息自动路由到 AI 对话引擎，记录 token 用量

### 模型用量
- **用量看板**: 每日 token 消耗柱状图、模型分布、token 构成分析
- **消费记录**: 最近调用记录列表，支持按时间范围筛选

### 外部集成
- **多模型支持**: 支持 OpenAI、Anthropic 等多种 LLM 模型，可配置多个供应商
- **工具集成**: 支持 Jira、Figma、GitHub、GitLab、Trello 等工具集成
- **组件库**: 可复用的产品组件管理系统

### 工作流管理
- **工作流编排**: 支持创建、暂停、恢复、取消工作流，8个预定义PM工作流
- **并行执行**: 支持步骤依赖管理和并行执行，自动分析依赖关系
- **文档查看**: Markdown预览、导出（MD/HTML/PDF）
- **校验报告**: 自动生成一致性检查和修复报告

### Sandbox 执行环境
- **安全隔离**: 本地子进程沙箱，支持 Shell/Python/HTTP 工具执行
- **资源控制**: CPU 60s 超时、512MB 内存、10MB 文件大小限制
- **安全管控**: 拦截 rm/sudo/shutdown 等危险命令，拦截 localhost/内网 IP/路径穿越
- **工作空间**: 自动创建 `/tmp/sandbox/{execution_id}/` 工作区，包含 inputs/outputs/temp 子目录
- **12个内置工具**: 文件工具（读写列删拷移）、Shell 工具（命令执行/脚本）、Python 工具（执行/脚本）、HTTP 工具（GET/POST）
- **流式事件**: SSE 实时推送执行进度、工具调用结果、文件创建事件
- **产物收集**: 自动收集执行产物并持久化

### 持久化记忆系统
- **多层级记忆**: 项目级（决策/模式/约束）、会话级（上下文/实体/任务状态）、用户级（偏好/风格）
- **自动提取**: 从工作流结果、Sandbox 执行、对话消息、用户反馈中自动提取关键信息
- **智能检索**: 按层级、关键词、相关性排序检索记忆，支持 Token 限制注入
- **偏好学习**: 自动学习用户语言偏好、输出格式、沟通风格
- **原子存储**: JSON 文件持久化 + gzip 归档，支持记忆去重
- **API 支持**: REST API 管理记忆的创建、检索、搜索、归档

## 快速开始

### 安装

```bash
pip install -e ".[dev]"
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入API密钥
```

### 运行

```bash
# 启动Web服务器
pm-workstation serve --reload

# 访问 http://localhost:8000 使用工作站
# 访问 http://localhost:8000/docs 查看API文档
```

## 开发

### 运行测试

```bash
pytest
```

### 代码检查

```bash
# Linting
ruff check src tests

# 格式化
ruff format src tests

# 类型检查
mypy src
```

## 项目结构

```
src/pm_workstation/
├── __init__.py          # 包初始化
├── cli.py               # CLI入口
├── config.py            # 配置管理
├── models/              # 数据模型
├── agents/              # Agent实现
│   ├── requirement.py   # 需求解析Agent
│   ├── prototype.py     # 原型Agent
│   ├── documentation.py # 文档Agent
│   ├── verification.py  # 校验Agent
│   └── coordinator_chat.py # 聊天协调Agent
├── chat/                # 聊天模块
│   ├── chat_manager.py  # 聊天会话管理
│   ├── task_router.py   # 任务路由分发
│   └── chat_models.py   # 聊天数据模型
├── channels/            # 渠道接入（飞书/企业微信）
├── component_library/   # 组件库（原型组件模板）
├── knowledge_base/      # 知识库（产品文档模板）
├── memory/              # 记忆系统（传统 + 持久化）
│   ├── memory_manager.py      # 传统记忆管理
│   ├── soul_manager.py        # Soul人格管理
│   ├── reflection_engine.py   # 反思引擎
│   ├── persistent_models.py   # 持久化记忆数据模型
│   ├── persistent_store.py    # 原子写入/索引/归档存储
│   ├── memory_extractor.py    # 自动提取记忆
│   ├── memory_retriever.py    # 记忆检索（关键词/层级/重要性）
│   ├── memory_applicator.py   # 记忆注入到 Agent 上下文
│   └── persistent_manager.py  # 持久化记忆管理器
├── sandbox/             # Sandbox 执行环境
│   ├── engine.py              # 执行引擎
│   ├── tool_manager.py        # 工具注册与调度
│   ├── workspace_manager.py   # 工作区管理
│   ├── process_executor.py    # 进程执行（超时控制）
│   ├── security_controller.py # 安全管控
│   ├── resource_monitor.py    # 资源监控
│   ├── models.py              # 数据模型
│   └── api/routes.py          # Sandbox REST + SSE API
├── skills/              # PM Skills技能系统
├── orchestrator/        # 流程编排器
├── llm/                 # LLM供应商管理
│   └── token_usage.py   # Token用量统计
├── storage/             # 存储层
├── integrations/        # 外部系统集成
├── document/            # 文档生成与格式化
├── verification/        # 校验与修复
├── prototype/           # 原型生成
└── api/                 # FastAPI应用
    └── routes/          # API路由
```

## 技术栈

- **后端**: Python 3.11+, FastAPI, LangChain, LangGraph
- **前端**: React, Next.js, TypeScript, TailwindCSS
- **数据库**: PostgreSQL, Redis
- **存储**: MinIO/S3
- **测试**: pytest, pytest-asyncio

## 许可证

MIT
