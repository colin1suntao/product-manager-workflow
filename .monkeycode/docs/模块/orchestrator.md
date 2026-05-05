# 工作流编排器模块 (orchestrator)

## 概述

工作流编排器基于 LangGraph 的状态图（StateGraph）实现，管理从需求解析到交付物生成的完整生命周期。通过状态机模式确保各阶段按正确的顺序执行，支持用户交互中断和恢复。

## 模块结构

```
src/pm_workstation/orchestrator/
├── __init__.py
├── workflow_state.py      # LangGraph 工作流状态定义
├── workflow_graph.py      # 状态图节点和边定义
└── workflow_manager.py    # 高层工作流管理接口
```

## 工作流状态 (`workflow_state.py`)

### WorkflowState

LangGraph 工作流中传递和共享的状态数据：

```python
class WorkflowState(BaseModel):
    workflow_run: WorkflowRun                    # 工作流运行记录
    structured_requirement: Optional[StructuredRequirement]  # 解析阶段产物
    reasoning_trace: str                         # 推理路径记录
    clarification_questions: list[dict]          # 待澄清问题列表
    page_structure: Optional[PageStructure]      # 页面结构
    prototype_html: str                          # 原型 HTML 内容
    prd_document: str                            # PRD 文档内容
    verification_report: Optional[VerificationReport]  # 校验报告
    error_message: Optional[str]                 # 错误信息
    pause_requested: bool                        # 是否请求暂停
    user_responses: list[dict]                   # 用户回复
```

#### 状态字段分组

| 阶段 | 字段 | 说明 |
|-----|------|------|
| 核心 | `workflow_run` | 工作流运行记录，包含 ID、用户 ID、需求文本、状态等 |
| 解析 | `structured_requirement`, `reasoning_trace`, `clarification_questions` | 需求解析产物 |
| 生成 | `page_structure`, `prototype_html`, `prd_document` | 原型和文档生成产物 |
| 校验 | `verification_report` | 校验报告 |
| 控制 | `error_message`, `pause_requested`, `user_responses` | 流程控制字段 |

#### 方法

| 方法 | 说明 |
|-----|------|
| `update_status(status: WorkflowStatus)` | 更新工作流状态并更新时间戳 |
| `to_dict() -> dict` | 转换为字典（用于 LangGraph 状态传递） |
| `from_dict(data: dict) -> WorkflowState` | 从字典恢复状态 |

---

## 工作流图 (`workflow_graph.py`)

### 状态转换图

```
START -> parse -> generate -> verify -> complete -> END
                |          |
                v          v
         handle_user_input  (fail)
                |
                v
              parse (循环)
```

### 节点定义 (WorkflowNodes)

| 节点名 | 对应方法 | 状态转换 | 说明 |
|-------|---------|---------|------|
| `parse` | `parsing_node()` | PARSING -> PARSED / WAITING_USER_INPUT / FAILED | 需求解析节点 |
| `generate` | `generating_node()` | GENERATING -> GENERATED / FAILED | 原型与文档生成节点 |
| `verify` | `verifying_node()` | VERIFYING -> VERIFIED / FAILED | 校验节点 |
| `complete` | `completing_node()` | VERIFIED -> COMPLETED | 完成节点 |
| `handle_user_input` | `handle_user_input_node()` | WAITING_USER_INPUT -> PARSING | 处理用户输入节点 |

### 节点详细说明

#### parse 节点

```python
@staticmethod
def parsing_node(state: WorkflowState) -> dict:
    """需求解析节点 (PARSING -> PARSED)"""
    state.update_status(WorkflowStatus.PARSING)
    
    if not state.workflow_run.requirement_text:
        raise ValueError("需求文本为空")
    
    if state.clarification_questions:
        state.update_status(WorkflowStatus.WAITING_USER_INPUT)
        return {"workflow_run": state.workflow_run, "clarification_questions": state.clarification_questions}
    
    state.update_status(WorkflowStatus.PARSED)
    return {"workflow_run": state.workflow_run}
```

**行为**:
1. 检查需求文本是否为空
2. 如果存在待澄清问题，进入 WAITING_USER_INPUT 状态
3. 否则标记为 PARSED

#### generate 节点

```python
@staticmethod
def generating_node(state: WorkflowState) -> dict:
    """原型与文档生成节点 (PARSED -> GENERATING -> GENERATED)"""
    state.update_status(WorkflowStatus.GENERATING)
    
    if not state.structured_requirement and not state.workflow_run.structured_requirement:
        raise ValueError("缺少结构化需求，无法生成")
    
    # 实际实现中会并行调用 PrototypeGenerator 和 DocumentGenerator
    state.update_status(WorkflowStatus.GENERATED)
    return {"workflow_run": state.workflow_run}
```

**行为**:
1. 检查是否存在结构化需求
2. 并行生成原型和 PRD 文档
3. 标记为 GENERATED

#### verify 节点

```python
@staticmethod
def verifying_node(state: WorkflowState) -> dict:
    """校验节点 (GENERATED -> VERIFYING -> VERIFIED)"""
    state.update_status(WorkflowStatus.VERIFYING)
    
    if state.pause_requested:
        state.update_status(WorkflowStatus.WAITING_USER_INPUT)
        return {"workflow_run": state.workflow_run}
    
    state.update_status(WorkflowStatus.VERIFIED)
    return {"workflow_run": state.workflow_run}
```

**行为**:
1. 调用 PrototypeVerifier、DocumentVerifier、ConsistencyChecker
2. AutoFixer 自动修复可修复问题
3. IssueReporter 生成报告
4. 如果请求暂停，进入 WAITING_USER_INPUT

#### complete 节点

```python
@staticmethod
def completing_node(state: WorkflowState) -> dict:
    """完成节点 (VERIFIED -> COMPLETED)"""
    state.update_status(WorkflowStatus.COMPLETED)
    return {"workflow_run": state.workflow_run}
```

#### handle_user_input 节点

```python
@staticmethod
def handle_user_input_node(state: WorkflowState) -> dict:
    """处理用户输入节点 (WAITING_USER_INPUT -> 恢复)"""
    if state.user_responses:
        state.update_status(WorkflowStatus.PARSING)
        return {"workflow_run": state.workflow_run, "user_responses": []}
    
    state.update_status(WorkflowStatus.WAITING_USER_INPUT)
    return {"workflow_run": state.workflow_run}
```

**行为**:
1. 如果用户已回复，清除等待状态，回到 PARSING
2. 否则继续等待

### 条件路由

| 条件函数 | 来源节点 | 可能目标 | 判断逻辑 |
|---------|---------|---------|---------|
| `should_proceed_to_generate` | parse | generate / handle_user_input | 如果有澄清问题且用户未回复，等待用户输入 |
| `should_handle_pause` | generate | handle_user_input / verify | 如果请求暂停，进入等待 |
| `should_proceed_to_complete` | verify | complete / END | 如果有错误消息，结束（失败）；如果已验证，进入完成 |

### 构建工作流图

```python
def build_workflow_graph() -> StateGraph:
    workflow = StateGraph(WorkflowState)
    
    # 添加节点
    workflow.add_node("parse", WorkflowNodes.parsing_node)
    workflow.add_node("generate", WorkflowNodes.generating_node)
    workflow.add_node("verify", WorkflowNodes.verifying_node)
    workflow.add_node("complete", WorkflowNodes.completing_node)
    workflow.add_node("handle_user_input", WorkflowNodes.handle_user_input_node)
    
    # 定义边
    workflow.add_edge(START, "parse")
    workflow.add_conditional_edges("parse", should_proceed_to_generate, {...})
    workflow.add_edge("handle_user_input", "parse")
    workflow.add_conditional_edges("generate", should_handle_pause, {...})
    workflow.add_conditional_edges("verify", should_proceed_to_complete, {...})
    workflow.add_edge("complete", END)
    
    return workflow

def create_workflow_app() -> object:
    """创建并编译工作流应用"""
    graph = build_workflow_graph()
    return graph.compile()
```

---

## 工作流管理器 (`workflow_manager.py`)

### WorkflowManager

提供高层工作流管理接口。

```python
class WorkflowManager:
    def __init__(self) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._app = create_workflow_app()
```

#### 方法列表

| 方法 | 参数 | 返回值 | 说明 |
|-----|------|--------|------|
| `start_workflow` | user_id, requirement_text, workflow_id? | WorkflowRun | 启动新工作流 |
| `get_workflow_status` | workflow_id | WorkflowRun? | 获取工作流状态 |
| `pause_workflow` | workflow_id | bool | 暂停工作流 |
| `resume_workflow` | workflow_id, user_responses? | bool | 恢复工作流 |
| `get_deliverables` | workflow_id | dict? | 获取交付物 |
| `list_workflows` | user_id? | list[WorkflowRun] | 列出工作流 |

#### start_workflow

```python
def start_workflow(
    self,
    user_id: str,
    requirement_text: str,
    workflow_id: Optional[str] = None,
) -> WorkflowRun:
    run_id = workflow_id or f"wf-{uuid.uuid4().hex[:12]}"
    run = WorkflowRun(
        id=run_id,
        user_id=user_id,
        requirement_text=requirement_text,
        status=WorkflowStatus.INIT,
    )
    self._runs[run_id] = run
    return run
```

#### pause_workflow

```python
def pause_workflow(self, workflow_id: str) -> bool:
    run = self._runs.get(workflow_id)
    if not run:
        return False
    if run.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
        return False
    run.update_status(WorkflowStatus.WAITING_USER_INPUT)
    return True
```

**限制**: 已完成或已失败的工作流不能暂停。

#### resume_workflow

```python
def resume_workflow(self, workflow_id: str, user_responses: Optional[list] = None) -> bool:
    run = self._runs.get(workflow_id)
    if not run:
        return False
    if run.status not in (WorkflowStatus.WAITING_USER_INPUT, WorkflowStatus.FAILED):
        return False
    run.update_status(WorkflowStatus.PARSING)
    return True
```

**限制**: 仅 WAITING_USER_INPUT 或 FAILED 状态的工作流可以恢复。

#### get_deliverables

```python
def get_deliverables(self, workflow_id: str) -> Optional[dict]:
    run = self._runs.get(workflow_id)
    if not run:
        return None
    return {
        "prototype_url": run.prototype_url,
        "prd_document_url": run.prd_document_url,
        "verification_report": run.verification_report,
    }
```

---

## WorkflowStatus 枚举

```python
class WorkflowStatus(str, Enum):
    INIT = "init"
    PARSING = "parsing"
    PARSED = "parsed"
    GENERATING = "generating"
    GENERATED = "generated"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_USER_INPUT = "waiting_user_input"
```

---

## 测试文件

| 测试文件 | 测试内容 |
|---------|---------|
| `tests/unit/test_orchestrator.py` | 工作流管理器、状态转换、节点逻辑 |
