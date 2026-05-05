# LLM 多供应商接入 - Implementation Task List

## Task 1: 创建 LLM 配置模型和存储
- [x] 1.1 创建 `src/pm_workstation/llm/__init__.py`
- [x] 1.2 创建 `src/pm_workstation/llm/models.py`，定义 LLMProviderConfig 模型
- [x] 1.3 创建 `src/pm_workstation/llm/provider_store.py`，实现 LLMProviderStore
- [x] 1.4 为 LLM 配置模块编写单元测试

## Task 2: 创建 LLM 工厂和适配器
- [x] 2.1 创建 `src/pm_workstation/llm/factory.py`，实现 LLMFactory
- [x] 2.2 扩展现有 `OpenAIAdapter` 和 `AnthropicAdapter`
- [x] 2.3 创建通用 `CustomAdapter` 支持 OpenAI 兼容格式
- [x] 2.4 为 LLM 工厂编写单元测试

## Task 3: 实现 LLM Provider API 路由
- [x] 3.1 创建 `src/pm_workstation/api/routes/llm.py`，实现 6 个端点
- [x] 3.2 在 `src/pm_workstation/api/app.py` 中注册 llm router
- [x] 3.3 创建 `src/pm_workstation/api/schemas.py` 中的 LLM 相关 Schema
- [x] 3.4 为 LLM API 路由编写单元测试

## Task 4: 工作流集成真实 LLM
- [x] 4.1 修改 `WorkflowManager` 支持 LLM Provider 参数
- [x] 4.2 修改 `WorkflowNodes` 使用真实 LLM 实例
- [x] 4.3 修改 `StartWorkflowRequest` 支持指定 llm_provider_id
- [x] 4.4 为工作流集成编写单元测试

## Task 5: 前端 LLM 配置页面
- [x] 5.1 创建 `frontend/src/app/settings/llm/page.tsx`
- [x] 5.2 创建 `frontend/src/lib/llm.ts` API 客户端
- [x] 5.3 实现 Provider 列表、创建、编辑、删除、测试功能
- [x] 5.4 更新工作流启动页面支持选择 LLM Provider

## Task 6: 端到端测试
- [x] 6.1 编写 E2E 测试验证完整工作流（使用 Mock LLM）
- [x] 6.2 编写 LLM Provider 管理 E2E 测试
- [x] 6.3 运行全量测试套件
