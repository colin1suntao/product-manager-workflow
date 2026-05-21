# AI 会话功能优化方案

## 背景

基于与 DeerFlow 项目的对比分析，本项目在 AI 会话功能方面存在以下关键差距：

1. **缺乏流式响应**: 无法实时展示 AI 思考过程，用户体验不佳
2. **缺乏工作流编排**: 无法组合多个技能形成完整创作流程
3. **缺乏 Sub-Agent 注册机制**: TaskRouter 硬编码，无法动态扩展
4. **缺乏产物管理**: 生成的原型/文档无法版本管理和迭代

## 优化目标

打造符合内容创作场景的 AI 会话系统，核心目标：

- **实时反馈**: 用户能看到 AI 的思考过程，而非等待最终结果
- **灵活编排**: 用户可以组合多个技能形成自定义工作流
- **动态扩展**: 系统可以轻松添加新的专业 Sub-Agent
- **产物可迭代**: 生成的原型/文档可以继续修改和完善

## Phase 1: 流式响应实现

### 设计方案

采用 Server-Sent Events (SSE) 实现流式响应：

```
Frontend                    Backend
   │                          │
   │ ─── POST /chat/stream ──▶│
   │                          │
   │◀── SSE: intent_analysis ─│ (意图分析完成)
   │◀── SSE: task_routing    ─│ (任务路由完成)
   │◀── SSE: skill_loading   ─│ (技能加载完成)
   │◀── SSE: executing       ─│ (开始执行)
   │◀── SSE: chunk_1         ─│ (生成内容片段)
   │◀── SSE: chunk_2         ─│
   │◀── SSE: chunk_3         ─│
   │                          │
   │◀── SSE: done            ─│ (完成)
   │                          │
```

### 技术实现

#### Backend: SSE API

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.post("/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
):
    """流式发送消息"""
    
    async def event_generator():
        # Step 1: Intent Analysis
        yield f"event: intent_analysis\ndata: {json.dumps({'intent': 'requirement', 'confidence': 0.95})}\n\n"
        
        # Step 2: Task Routing
        yield f"event: task_routing\ndata: {json.dumps({'mode': 'REQUIREMENT', 'skills': ['user-story']})}\n\n"
        
        # Step 3: Execute with streaming
        coordinator = await _get_coordinator(request)
        
        async for chunk in coordinator.stream_process_message(
            message=content,
            context=context,
            selected_skills=selected_skills,
        ):
            yield f"event: chunk\ndata: {json.dumps({'content': chunk})}\n\n"
        
        # Step 4: Done
        yield f"event: done\ndata: {json.dumps({'message_id': 'xxx', 'artifacts': []})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

#### Frontend: SSE Client

```typescript
// lib/streamingApi.ts
export class StreamingChatClient {
  private eventSource: EventSource | null = null;
  
  async sendMessage(
    sessionId: string,
    content: string,
    onEvent: (event: StreamEvent) => void
  ): Promise<void> {
    // POST first to get session, then connect SSE
    const response = await fetch(`/api/v1/chat/sessions/${sessionId}/stream`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const text = decoder.decode(value);
      const lines = text.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7);
          // Parse data line
          const dataLine = lines[lines.indexOf(line) + 1];
          if (dataLine?.startsWith('data: ')) {
            const data = JSON.parse(dataLine.slice(6));
            onEvent({ type: eventType, data });
          }
        }
      }
    }
  }
}

// Usage
const client = new StreamingChatClient();
await client.sendMessage(sessionId, content, (event) => {
  switch (event.type) {
    case 'intent_analysis':
      setIntent(event.data);
      break;
    case 'task_routing':
      setTaskMode(event.data.mode);
      break;
    case 'chunk':
      appendContent(event.data.content);
      break;
    case 'done':
      finalizeMessage(event.data);
      break;
  }
});
```

### UI 设计

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 正在分析意图...                                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 意图: 需求分析                                           ││
│  │ 置信度: 95%                                             ││
│  │ 建议技能: user-story, jobs-to-be-done                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  📋 任务路由完成                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 模式: REQUIREMENT                                        ││
│  │ 技能: user-story                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ⚡ 正在生成内容...                                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ # 用户故事                                               ││
│  │                                                          ││
│  │ 作为一名电商平台的用户，                                   ││
│  │ 我想要能够快速筛选商品，                                   ││
│  │ 以便节省购物时间...                                       ││
│  │                                                          ││
│  │ [实时滚动展示生成内容]                                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ⏱️ 已用时: 12.5s | Token: 856                               │
└─────────────────────────────────────────────────────────────┘
```

## Phase 2: 工作流编排

### 设计方案

创建 WorkflowOrchestrator 支持多步骤任务组合：

```python
class WorkflowOrchestrator:
    """工作流编排器
    
    支持将多个任务步骤组合成完整工作流。
    """
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        user_id: str,
        context: dict,
    ) -> WorkflowResult:
        """执行工作流"""
        
        results = []
        for step in workflow.steps:
            # 检查依赖条件
            if step.depends_on:
                dep_result = results[step.depends_on]
                if dep_result.status != TaskStatus.COMPLETED:
                    raise WorkflowError(f"Dependency {step.depends_on} failed")
                
                # 将依赖结果作为输入
                step.input = dep_result.output
            
            # 执行步骤
            result = await self.task_router.execute_task(
                mode=step.mode,
                params=step.input,
                selected_skills=step.skills,
            )
            results.append(result)
            
            # 检查是否可以并行执行后续步骤
            parallel_steps = [s for s in workflow.steps if s.parallel_with == step.id]
            if parallel_steps:
                parallel_results = await asyncio.gather(*[
                    self.task_router.execute_task(s.mode, s.input, s.skills)
                    for s in parallel_steps
                ])
                results.extend(parallel_results)
        
        return WorkflowResult(steps=results)
```

### WorkflowDefinition 数据模型

```python
class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str
    name: str
    mode: TaskMode
    skills: list[str] = []
    depends_on: Optional[str] = None  # 依赖的步骤 ID
    parallel_with: Optional[str] = None  # 并行执行的步骤 ID
    input: dict = {}
    timeout: int = 90  # 超时秒数

class WorkflowDefinition(BaseModel):
    """工作流定义"""
    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    estimated_time: str  # 如 "5-10 minutes"
    best_for: list[str]  # 适用场景

class WorkflowResult(BaseModel):
    """工作流执行结果"""
    workflow_id: str
    steps: list[TaskResult]
    artifacts: list[Artifact]
    total_time: float
    status: WorkflowStatus
```

### 预定义工作流

```python
# workflows/pm_workflows.py

PM_WORKFLOWS = [
    WorkflowDefinition(
        id="full-product-design",
        name="完整产品设计流程",
        description="从需求分析到原型设计和文档撰写的完整流程",
        steps=[
            WorkflowStep(
                id="step-1",
                name="需求分析",
                mode=TaskMode.REQUIREMENT,
                skills=["user-story", "jobs-to-be-done"],
            ),
            WorkflowStep(
                id="step-2",
                name="原型设计",
                mode=TaskMode.PROTOTYPE,
                skills=["huashu-design"],
                depends_on="step-1",  # 依赖需求分析结果
            ),
            WorkflowStep(
                id="step-3",
                name="PRD撰写",
                mode=TaskMode.PRD,
                skills=["prd-template"],
                depends_on="step-1",  # 依赖需求分析结果
                parallel_with="step-2",  # 与原型设计并行
            ),
        ],
        estimated_time="10-15 minutes",
        best_for=["新产品设计", "功能迭代", "从0到1"],
    ),
    
    WorkflowDefinition(
        id="market-research-full",
        name="完整市场调研流程",
        description="市场分析 + 竞品研究 + 用户洞察",
        steps=[
            WorkflowStep(
                id="step-1",
                name="市场分析",
                mode=TaskMode.MARKET_RESEARCH,
                skills=["pestel-analysis", "tam-sam-som-calculator"],
            ),
            WorkflowStep(
                id="step-2",
                name="竞品研究",
                mode=TaskMode.MARKET_RESEARCH,
                skills=["competitive-analysis"],
                parallel_with="step-1",  # 与市场分析并行
            ),
            WorkflowStep(
                id="step-3",
                name="用户洞察",
                mode=TaskMode.MARKET_RESEARCH,
                skills=["customer-journey-map", "discovery-interview-prep"],
                depends_on="step-1",
            ),
        ],
        estimated_time="15-20 minutes",
        best_for=["市场进入决策", "竞品分析", "用户研究"],
    ),
]
```

### API 设计

```python
@router.get("/workflows", summary="获取预定义工作流列表")
async def list_workflows() -> dict:
    """获取预定义的工作流模板"""
    return {
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "steps": len(w.steps),
                "estimated_time": w.estimated_time,
                "best_for": w.best_for,
            }
            for w in PM_WORKFLOWS
        ]
    }

@router.post("/workflows/{workflow_id}/execute", summary="执行工作流")
async def execute_workflow(
    workflow_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """执行预定义工作流"""
    orchestrator = WorkflowOrchestrator()
    workflow = get_workflow(workflow_id)
    
    result = await orchestrator.execute_workflow(
        workflow=workflow,
        user_id=user_id,
        context=body.get("context", {}),
    )
    
    return result.model_dump()
```

### UI 设计

```
┌─────────────────────────────────────────────────────────────┐
│  📋 工作流选择                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [完整产品设计流程]                                        ││
│  │ 从需求分析到原型和文档                                     ││
│  │ 步骤: 3 | 预估: 10-15分钟                                 ││
│  │ 适用: 新产品设计、功能迭代                                 ││
│  │                                          [▶ 开始执行]    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  🔄 执行进度                                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 1: 需求分析 ✅ 完成 (用时: 45s)                      ││
│  │         ├─ 技能: user-story, jobs-to-be-done             ││
│  │         └─ 产物: user_stories.md                         ││
│  │                                                          ││
│  │ Step 2: 原型设计 🔄 进行中 (用时: 30s)                    ││
│  │         ├─ 技能: huashu-design                           ││
│  │         └─ 预览: [实时更新]                               ││
│  │                                                          ││
│  │ Step 3: PRD撰写 ⏸️ 等待 (与 Step 2 并行)                 ││
│  │         ├─ 技能: prd-template                            ││
│  │                                                          ││
│  │ [████████████████░░░░░░░░░░] 67%                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  📦 产物预览                                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [user_stories.md] [prototype.html] [prd.md]              ││
│  │                                          [下载全部]       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Phase 3: Sub-Agent 注册机制

### 设计方案

创建 SubAgentRegistry 支持动态注册和能力匹配：

```python
class SubAgentConfig(BaseModel):
    """Sub-Agent 配置"""
    agent_id: str
    name: str
    description: str
    capabilities: list[str]  # 能力标签: ["requirement", "prototype", "prd"]
    default_skills: list[str] = []
    system_prompt: str = ""
    tools: list[str] = []
    timeout: int = 90
    max_retries: int = 2

class SubAgentRegistry:
    """Sub-Agent 注册表
    
    管理所有已注册的 Sub-Agent，支持能力匹配。
    """
    
    _agents: dict[str, SubAgentConfig] = {}
    
    def register(self, config: SubAgentConfig) -> None:
        """注册 Sub-Agent"""
        self._agents[config.agent_id] = config
    
    def unregister(self, agent_id: str) -> None:
        """注销 Sub-Agent"""
        self._agents.pop(agent_id, None)
    
    def get(self, agent_id: str) -> Optional[SubAgentConfig]:
        """获取 Sub-Agent 配置"""
        return self._agents.get(agent_id)
    
    def match_by_capability(self, capability: str) -> list[SubAgentConfig]:
        """根据能力匹配 Sub-Agent"""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]
    
    def list_all(self) -> list[SubAgentConfig]:
        """列出所有 Sub-Agent"""
        return list(self._agents.values())
```

### 预注册 Sub-Agent

```python
# agents/sub_agents.py

def register_pm_sub_agents(registry: SubAgentRegistry) -> None:
    """注册 PM 专业 Sub-Agent"""
    
    registry.register(SubAgentConfig(
        agent_id="requirement-analyst",
        name="需求分析师",
        description="专业的需求分析和用户故事撰写 Agent",
        capabilities=["requirement", "user-story", "jobs-to-be-done"],
        default_skills=["user-story", "jobs-to-be-done"],
        system_prompt="你是一名专业的需求分析师...",
        timeout=60,
    ))
    
    registry.register(SubAgentConfig(
        agent_id="prototype-designer",
        name="原型设计师",
        description="使用 huashu-design 方法论的高保真原型 Agent",
        capabilities=["prototype", "ui-design", "interaction"],
        default_skills=["huashu-design"],
        system_prompt="你是一名专业的原型设计师...",
        timeout=90,
    ))
    
    registry.register(SubAgentConfig(
        agent_id="prd-writer",
        name="PRD撰写专家",
        description="专业的产品需求文档撰写 Agent",
        capabilities=["prd", "documentation", "specification"],
        default_skills=["prd-template"],
        system_prompt="你是一名专业的文档撰写专家...",
        timeout=60,
    ))
    
    registry.register(SubAgentConfig(
        agent_id="market-researcher",
        name="市场研究员",
        description="市场分析和竞品研究 Agent",
        capabilities=["market-research", "competitive-analysis", "pestel"],
        default_skills=["pestel-analysis", "tam-sam-som-calculator"],
        system_prompt="你是一名专业的市场研究员...",
        timeout=90,
    ))
```

### SubAgentExecutor

```python
class SubAgentExecutor:
    """Sub-Agent 执行器
    
    执行单个 Sub-Agent 的任务，支持上下文隔离。
    """
    
    async def execute(
        self,
        agent_config: SubAgentConfig,
        task_params: dict,
        context: Optional[IsolatedContext] = None,
        llm_handler: Optional[LLMBackend] = None,
    ) -> TaskResult:
        """执行 Sub-Agent 任务"""
        
        # 创建隔离上下文
        if not context:
            context = IsolatedContext(
                agent_id=agent_config.agent_id,
                task_id=self._generate_task_id(),
                messages=[],
                workspace=f"/tmp/workspace/{agent_config.agent_id}",
            )
        
        # 加载技能
        skills = self.skill_loader.load_skills(agent_config.default_skills)
        
        # 构建系统提示词
        system_prompt = agent_config.system_prompt
        for skill in skills:
            system_prompt += f"\n\n{skill.system_prompt}"
        
        # 执行任务
        try:
            result = await asyncio.wait_for(
                self._run_agent(
                    llm_handler=llm_handler,
                    system_prompt=system_prompt,
                    task_params=task_params,
                    context=context,
                ),
                timeout=agent_config.timeout,
            )
            
            return TaskResult(
                task_id=context.task_id,
                task_mode=TaskMode.CUSTOM,
                status=TaskStatus.COMPLETED,
                output=result,
            )
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=context.task_id,
                status=TaskStatus.FAILED,
                error_message=f"Agent timeout after {agent_config.timeout}s",
            )
```

### API 设计

```python
@router.get("/sub-agents", summary="获取 Sub-Agent 列表")
async def list_sub_agents() -> dict:
    """获取所有已注册的 Sub-Agent"""
    registry = get_sub_agent_registry()
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "default_skills": a.default_skills,
            }
            for a in registry.list_all()
        ]
    }

@router.post("/sub-agents/{agent_id}/execute", summary="执行 Sub-Agent")
async def execute_sub_agent(
    agent_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """执行指定 Sub-Agent"""
    registry = get_sub_agent_registry()
    config = registry.get(agent_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Sub-Agent not found")
    
    executor = SubAgentExecutor()
    result = await executor.execute(
        agent_config=config,
        task_params=body.get("params", {}),
    )
    
    return result.model_dump()

@router.post("/sub-agents/match", summary="能力匹配")
async def match_sub_agents(body: dict) -> dict:
    """根据能力匹配 Sub-Agent"""
    capability = body.get("capability")
    registry = get_sub_agent_registry()
    
    matched = registry.match_by_capability(capability)
    return {
        "matched_agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "capabilities": a.capabilities,
            }
            for a in matched
        ]
    }
```

## Phase 4: 产物管理

### 设计方案

创建 ArtifactManager 支持产物版本管理和迭代：

```python
class ArtifactVersion(BaseModel):
    """产物版本"""
    version_id: str
    version_number: int
    content: str
    created_at: datetime
    created_by: str  # user_id or agent_id
    diff_from_previous: Optional[str] = None  # 与上一版本的差异

class Artifact(BaseModel):
    """产物"""
    artifact_id: str
    name: str
    type: str  # prototype, document, report, etc.
    session_id: str
    workflow_id: Optional[str] = None
    versions: list[ArtifactVersion] = []
    current_version: int = 0
    tags: list[str] = []

class ArtifactManager:
    """产物管理器
    
    支持产物的版本管理、迭代和下载。
    """
    
    def __init__(self, storage_path: str = "/tmp/artifacts"):
        self.storage_path = storage_path
    
    async def create(
        self,
        name: str,
        type: str,
        content: str,
        session_id: str,
        workflow_id: Optional[str] = None,
    ) -> Artifact:
        """创建新产物"""
        artifact_id = uuid.uuid4().hex
        
        artifact = Artifact(
            artifact_id=artifact_id,
            name=name,
            type=type,
            session_id=session_id,
            workflow_id=workflow_id,
            versions=[
                ArtifactVersion(
                    version_id=f"{artifact_id}-v1",
                    version_number=1,
                    content=content,
                    created_at=datetime.now(),
                    created_by="system",
                )
            ],
            current_version=1,
        )
        
        # 持久化
        await self._save_artifact(artifact)
        
        return artifact
    
    async def update(
        self,
        artifact_id: str,
        new_content: str,
        created_by: str,
    ) -> Artifact:
        """更新产物（创建新版本）"""
        artifact = await self.get(artifact_id)
        
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        # 计算差异
        prev_version = artifact.versions[-1]
        diff = self._compute_diff(prev_version.content, new_content)
        
        # 创建新版本
        new_version_number = len(artifact.versions) + 1
        new_version = ArtifactVersion(
            version_id=f"{artifact_id}-v{new_version_number}",
            version_number=new_version_number,
            content=new_content,
            created_at=datetime.now(),
            created_by=created_by,
            diff_from_previous=diff,
        )
        
        artifact.versions.append(new_version)
        artifact.current_version = new_version_number
        
        await self._save_artifact(artifact)
        
        return artifact
    
    async def get(self, artifact_id: str) -> Optional[Artifact]:
        """获取产物"""
        path = f"{self.storage_path}/{artifact_id}.json"
        if os.path.exists(path):
            with open(path) as f:
                return Artifact.model_validate(json.load(f))
        return None
    
    async def get_version(
        self,
        artifact_id: str,
        version_number: int,
    ) -> Optional[ArtifactVersion]:
        """获取指定版本的产物"""
        artifact = await self.get(artifact_id)
        if artifact:
            for v in artifact.versions:
                if v.version_number == version_number:
                    return v
        return None
    
    async def list_by_session(self, session_id: str) -> list[Artifact]:
        """获取会话的所有产物"""
        artifacts = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                artifact = await self.get(filename[:-5])
                if artifact and artifact.session_id == session_id:
                    artifacts.append(artifact)
        return artifacts
```

### API 设计

```python
@router.post("/artifacts", summary="创建产物")
async def create_artifact(
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建新产物"""
    manager = ArtifactManager()
    
    artifact = await manager.create(
        name=body.get("name"),
        type=body.get("type"),
        content=body.get("content"),
        session_id=body.get("session_id"),
        workflow_id=body.get("workflow_id"),
    )
    
    return artifact.model_dump()

@router.patch("/artifacts/{artifact_id}", summary="更新产物")
async def update_artifact(
    artifact_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """更新产物（创建新版本）"""
    manager = ArtifactManager()
    
    artifact = await manager.update(
        artifact_id=artifact_id,
        new_content=body.get("content"),
        created_by=user_id,
    )
    
    return artifact.model_dump()

@router.get("/artifacts/{artifact_id}", summary="获取产物")
async def get_artifact(
    artifact_id: str,
    version: Optional[int] = None,
) -> dict:
    """获取产物（可选指定版本）"""
    manager = ArtifactManager()
    
    if version:
        v = await manager.get_version(artifact_id, version)
        if v:
            return v.model_dump()
        raise HTTPException(status_code=404, detail="Version not found")
    
    artifact = await manager.get(artifact_id)
    if artifact:
        return artifact.model_dump()
    
    raise HTTPException(status_code=404, detail="Artifact not found")

@router.get("/sessions/{session_id}/artifacts", summary="获取会话产物")
async def list_session_artifacts(
    session_id: str,
) -> dict:
    """获取会话的所有产物"""
    manager = ArtifactManager()
    artifacts = await manager.list_by_session(session_id)
    
    return {
        "artifacts": [a.model_dump() for a in artifacts],
        "total": len(artifacts),
    }
```

### UI 设计

```
┌─────────────────────────────────────────────────────────────┐
│  📦 产物管理                                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 名称: user_stories.md                                   ││
│  │ 类型: document                                          ││
│  │ 当前版本: v3                                             ││
│  │ 创建时间: 2026-05-21 10:30                               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  📜 版本历史                                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ v1 (2026-05-21 10:30) - by requirement-analyst          ││
│  │    初始版本                                              ││
│  │                                          [查看] [回滚]    ││
│  │                                                          ││
│  │ v2 (2026-05-21 10:35) - by user                         ││
│  │    添加了验收标准                                        ││
│  │                                          [查看] [回滚]    ││
│  │                                                          ││
│  │ v3 (2026-05-21 10:40) - by user [当前]                  ││
│  │    补充了优先级排序                                      ││
│  │                                          [查看]          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  [编辑产物] [下载] [分享]                                     │
└─────────────────────────────────────────────────────────────┘
```

## 实施计划

### 优先级排序

| 功能 | 优先级 | 预估工时 | 用户价值 |
|------|--------|----------|----------|
| 流式响应 | P0 | 2-3天 | 实时反馈，显著提升体验 |
| Sub-Agent 注册机制 | P0 | 2天 | 动态扩展，基础架构 |
| 工作流编排 | P1 | 3-4天 | 组合技能，内容创作核心 |
| 产物管理 | P1 | 2天 | 版本管理，迭代能力 |
| 记忆持久化 | P2 | 1天 | 长期记忆，重启不丢失 |
| 按需加载技能 | P2 | 1天 | 节省 Token，提升效率 |

### 实施步骤

**Week 1**:
- Day 1-2: 实现流式响应 SSE API + 前端组件
- Day 3: 实现流式 CoordinatorChatAgent
- Day 4: 实现 SubAgentRegistry 和 SubAgentExecutor
- Day 5: 注册 PM Sub-Agent + 测试

**Week 2**:
- Day 1-2: 实现 WorkflowOrchestrator + 预定义工作流
- Day 3: 实现工作流 API + 前端 UI
- Day 4: 实现 ArtifactManager + 版本管理
- Day 5: 集成测试 + 文档

**Week 3**:
- Day 1: 记忆持久化 (SQLite)
- Day 2: 按需加载技能
- Day 3: Channel 命令支持
- Day 4: Token 精确统计
- Day 5: 整体优化 + 性能测试

## 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 用户满意度 (NPS) | 未知 | +30 |
| 平均响应感知时间 | 30-60秒等待 | 5秒内可见内容 |
| 技能组合使用率 | 0% (单一模式) | 60% (工作流) |
| 产物迭代率 | 0% (一次性) | 40% (多版本) |
| Sub-Agent 数量 | 4 (硬编码) | 10+ (可扩展) |

## 总结

本优化方案聚焦于内容创作场景的核心需求：

1. **流式响应** - 让用户实时看到 AI 的思考和创作过程
2. **工作流编排** - 让用户可以组合多个技能形成完整创作流程
3. **Sub-Agent 注册** - 让系统可以轻松扩展专业能力
4. **产物管理** - 让创作产物可以持续迭代和完善

这些优化将使本项目的 AI 会话系统从 "Chat + Skills" 升级为真正的 "PM Super Agent"，既保持 PM Skills 的专业性，又具备真实的创作和迭代能力。