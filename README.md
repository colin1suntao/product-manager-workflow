# 产品经理多Agent协作工作站

基于Python + LangChain的多Agent协作系统，集需求解析、原型绘制、文档编撰、校验纠错于一体。

## 功能特性

- **需求解析Agent**: 依托长链推理能力，精准解析碎片化业务需求
- **原型Agent**: 自动生成HTML/CSS/JS可交互原型
- **文档Agent**: 自动编撰标准化PRD文档
- **校验Agent**: 双向核验原型和文档，修复逻辑漏洞
- **多模型支持**: 支持OpenAI、Anthropic等多种LLM模型
- **外部集成**: 支持Jira、Figma、GitHub等工具集成

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
│   └── verification.py  # 校验Agent
├── orchestrator/        # 流程编排器
├── models/              # 模型路由器
├── storage/             # 存储层
├── integrations/        # 外部系统集成
└── api/                 # FastAPI应用
```

## 技术栈

- **后端**: Python 3.11+, FastAPI, LangChain, LangGraph
- **前端**: React, Next.js, TypeScript, TailwindCSS
- **数据库**: PostgreSQL, Redis
- **存储**: MinIO/S3
- **测试**: pytest, pytest-asyncio

## 许可证

MIT
