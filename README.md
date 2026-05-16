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
- **工作流编排**: 支持创建、暂停、恢复、取消工作流
- **文档查看**: Markdown预览、导出（MD/HTML/PDF）
- **校验报告**: 自动生成一致性检查和修复报告

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
├── memory/              # 记忆系统
│   ├── memory_manager.py    # 记忆管理
│   ├── soul_manager.py      # Soul人格管理
│   ├── memory_retriever.py  # 记忆检索
│   └── reflection_engine.py # 反思引擎
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
