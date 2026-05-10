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
- **长期记忆系统**: Agent具备Soul人格、偏好记忆、经验学习、反思能力
- **多任务模式**: 需求分析、原型生成、PRD编写、市场调研

### PM Skills技能系统
- **53个专业技能**: 涵盖市场分析、用户研究、产品规划、文档撰写等领域
- **技能模板**: 支持保存和加载技能组合模板
- **智能推荐**: 根据需求自动推荐相关技能

### 外部集成
- **多模型支持**: 支持OpenAI、Anthropic等多种LLM模型，可配置多个供应商
- **工具集成**: 支持Jira、Figma、GitHub、GitLab、Trello等工具集成
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
├── memory/              # 记忆系统
│   ├── memory_manager.py    # 记忆管理
│   ├── soul_manager.py      # Soul人格管理
│   ├── memory_retriever.py  # 记忆检索
│   └── reflection_engine.py # 反思引擎
├── skills/              # PM Skills技能系统
├── orchestrator/        # 流程编排器
├── llm/                 # LLM供应商管理
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
