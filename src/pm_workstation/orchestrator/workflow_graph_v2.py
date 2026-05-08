"""LangGraph 工作流图定义 V2 - DeerFlow 2.0 多 Agent 协作模式

基于 Coordinator Agent + Sub-agent 委派模式的工作流。
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from pm_workstation.agents.coordinator import CoordinatorAgent
from pm_workstation.agents.middlewares import (
    AuditMiddleware,
    ErrorHandlingMiddleware,
    MiddlewareChain,
    SummarizationMiddleware,
)
from pm_workstation.agents.registry import SubAgentConfig, SubAgentRegistry
from pm_workstation.agents.task_tool import (
    ContextManager,
    SubAgentExecutor,
    TaskDelegationTool,
)
from pm_workstation.models.core import WorkflowStatus
from pm_workstation.orchestrator.workflow_graph import WorkflowNodes
from pm_workstation.orchestrator.workflow_state import WorkflowState
from pm_workstation.skills.loader import SkillLoader

logger = logging.getLogger(__name__)


def _create_coordinator(llm_handler) -> CoordinatorAgent:
    """创建 Coordinator Agent 实例"""
    # 1. 加载 Sub-agent 配置
    registry = SubAgentRegistry()
    # 注册默认的 5 个 agent
    default_agents = [
        ("analyst", "需求分析师", "分析需求，提取实体、角色、流程和规则", ["requirement-analysis"]),
        ("writer", "PRD 写手", "根据需求生成标准 PRD 文档", ["prd-generation"]),
        ("designer", "原型设计师", "设计高保真 HTML 原型", ["prototype-generation"]),
        ("reviewer", "文档审阅员", "审阅 PRD 文档质量", ["document-review"]),
        ("qa", "校验员", "校验原型和文档的一致性", ["consistency-check"]),
    ]
    for agent_id, name, desc, skills in default_agents:
        registry.register(SubAgentConfig(
            id=agent_id,
            name=name,
            description=desc,
            system_prompt=f"你是{name}",
            skills=skills,
        ))

    # 2. 创建技能加载器
    skill_loader = SkillLoader()

    # 3. 创建上下文管理器
    context_manager = ContextManager()

    # 4. 创建执行器
    executor = SubAgentExecutor(
        llm_factory=llm_handler,
        context_manager=context_manager,
        skill_loader=skill_loader,
    )

    # 5. 创建委派工具
    task_tool = TaskDelegationTool(
        registry=registry,
        executor=executor,
        max_concurrent=3,
    )

    # 6. 创建中间件链
    middleware_chain = MiddlewareChain([
        AuditMiddleware(),
        ErrorHandlingMiddleware(max_retries=2),
        SummarizationMiddleware(max_output_length=4000),
    ])

    return CoordinatorAgent(
        llm_handler=llm_handler,
        registry=registry,
        task_tool=task_tool,
        middleware_chain=middleware_chain,
    )


class WorkflowNodesV2:
    """V2 工作流节点定义

    使用 Coordinator Agent 进行任务拆解和委派。
    """

    @staticmethod
    def parsing_node(state: WorkflowState, llm_handler=None) -> dict:
        """需求解析节点 (PARSING -> PARSED)

        V2 版本：使用 Coordinator Agent 进行智能拆解。
        """
        state.update_status(WorkflowStatus.PARSING)

        try:
            if not state.workflow_run.requirement_text:
                raise ValueError("需求文本为空")

            if llm_handler:
                # 使用 Coordinator Agent 拆解任务
                coordinator = _create_coordinator(llm_handler)

                result = WorkflowNodesV2._call_coordinator_sync(
                    coordinator, state.workflow_run.requirement_text
                )

                if result:
                    # 保存任务拆解结果
                    state.task_decomposition = result
                    state.coordinator_summary = result.get("summary", "")

                    # 如果 Coordinator 产生了结构化需求，保存它
                    if "structured_requirement" in result:
                        state.structured_requirement = result["structured_requirement"]

            # 如果存在澄清问题，进入等待用户输入
            if state.clarification_questions:
                state.update_status(WorkflowStatus.WAITING_USER_INPUT)
                return {
                    "workflow_run": state.workflow_run,
                    "clarification_questions": state.clarification_questions,
                }

            state.update_status(WorkflowStatus.PARSED)
            return {
                "workflow_run": state.workflow_run,
                "task_decomposition": state.task_decomposition,
                "coordinator_summary": state.coordinator_summary,
            }

        except Exception as e:
            logger.warning(f"[ParsingNodeV2] Coordinator parsing failed: {e}")
            # 降级到原有逻辑
            return WorkflowNodes.parsing_node(state, llm_handler)

    @staticmethod
    def _call_coordinator_sync(coordinator: CoordinatorAgent, requirement_text: str) -> dict | None:
        """同步调用 Coordinator Agent，带超时控制"""
        import asyncio
        import threading

        result_holder = {"value": None, "error": None}

        def _run_async():
            """在新线程中创建独立事件循环运行异步代码"""
            try:
                result_holder["value"] = asyncio.run(
                    coordinator.process_request(requirement_text)
                )
            except Exception as e:
                result_holder["error"] = e

        thread = threading.Thread(target=_run_async, daemon=True)
        thread.start()
        thread.join(timeout=30)  # 30 秒超时

        if thread.is_alive():
            raise TimeoutError("Coordinator call timed out after 30s")

        if result_holder["error"]:
            raise result_holder["error"]

        return result_holder["value"]

    @staticmethod
    def generating_node(state: WorkflowState, llm_handler=None) -> dict:
        """生成节点 (PARSED -> GENERATING -> GENERATED)

        V2 版本：如果 Coordinator 已经委派了生成任务，直接使用结果。
        否则降级到原有逻辑。
        """
        state.update_status(WorkflowStatus.GENERATING)

        try:
            # 检查 Coordinator 是否已经生成了结果
            if state.task_decomposition and state.subtask_results:
                # 从子任务结果中提取原型和 PRD
                for task_id, result in state.subtask_results.items():
                    if isinstance(result, dict):
                        if result.get("agent_id") == "designer" and result.get("status") == "success":
                            state.prototype_html = result.get("output", state.prototype_html)
                        elif result.get("agent_id") == "writer" and result.get("status") == "success":
                            state.prd_document = result.get("output", state.prd_document)

            # 如果仍然没有内容，使用原有逻辑
            if not state.prototype_html or not state.prd_document:
                req_text = state.workflow_run.requirement_text
                if not req_text:
                    raise ValueError("缺少需求文本，无法生成")

                if llm_handler:
                    if not state.prototype_html:
                        try:
                            prototype_html = WorkflowNodes._call_llm_sync(
                                llm_handler, "prototype", req_text
                            )
                            if prototype_html:
                                state.prototype_html = prototype_html
                        except Exception as e:
                            logger.warning(f"[GeneratingNodeV2] Prototype failed: {e}")

                    if not state.prd_document:
                        try:
                            prd_document = WorkflowNodes._call_llm_sync(
                                llm_handler, "prd", req_text
                            )
                            if prd_document:
                                state.prd_document = prd_document
                        except Exception as e:
                            logger.warning(f"[GeneratingNodeV2] PRD failed: {e}")

                # 兜底
                if not state.prototype_html:
                    state.prototype_html = WorkflowNodes._generate_simple_prototype(
                        state.workflow_run.requirement_text
                    )
                if not state.prd_document:
                    state.prd_document = WorkflowNodes._generate_simple_prd(
                        state.workflow_run.requirement_text
                    )

            state.update_status(WorkflowStatus.GENERATED)
            return {
                "workflow_run": state.workflow_run,
                "prototype_html": state.prototype_html,
                "prd_document": state.prd_document,
            }

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def verifying_node(state: WorkflowState) -> dict:
        """校验节点 - 复用原有逻辑"""
        return WorkflowNodes.verifying_node(state)

    @staticmethod
    def completing_node(state: WorkflowState) -> dict:
        """完成节点 - 复用原有逻辑"""
        return WorkflowNodes.completing_node(state)

    @staticmethod
    def handle_user_input_node(state: WorkflowState) -> dict:
        """处理用户输入节点 - 复用原有逻辑"""
        return WorkflowNodes.handle_user_input_node(state)


def should_proceed_to_generate_v2(state: WorkflowState) -> Literal["generate", "wait_for_user"]:
    """判断是否进入生成阶段 - V2"""
    if state.clarification_questions and not state.user_responses:
        return "wait_for_user"
    return "generate"


def should_proceed_to_complete_v2(state: WorkflowState) -> Literal["complete", "failed"]:
    """判断是否进入完成阶段 - V2"""
    if state.error_message:
        return "failed"
    if state.workflow_run.status == WorkflowStatus.VERIFIED:
        return "complete"
    return "failed"


def should_handle_generate_result_v2(state: WorkflowState) -> Literal["verify", "failed", "pause"]:
    """判断生成节点执行结果 - V2"""
    if state.error_message:
        return "failed"
    if state.pause_requested:
        return "pause"
    return "verify"


def build_workflow_graph_v2(llm_handler=None) -> StateGraph:
    """构建 V2 工作流图

    使用 Coordinator Agent + Sub-agent 委派模式，但保持与 V1 相同的 API 和状态转换。
    """
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("parse", lambda state: WorkflowNodesV2.parsing_node(state, llm_handler))
    workflow.add_node("generate", lambda state: WorkflowNodesV2.generating_node(state, llm_handler))
    workflow.add_node("verify", WorkflowNodesV2.verifying_node)
    workflow.add_node("complete", WorkflowNodesV2.completing_node)
    workflow.add_node("handle_user_input", WorkflowNodesV2.handle_user_input_node)

    # 定义边
    workflow.add_edge(START, "parse")

    workflow.add_conditional_edges(
        "parse",
        should_proceed_to_generate_v2,
        {
            "generate": "generate",
            "wait_for_user": "handle_user_input",
        },
    )

    workflow.add_edge("handle_user_input", "parse")

    workflow.add_conditional_edges(
        "generate",
        should_handle_generate_result_v2,
        {
            "verify": "verify",
            "pause": "handle_user_input",
            "failed": END,
        },
    )

    workflow.add_conditional_edges(
        "verify",
        should_proceed_to_complete_v2,
        {
            "complete": "complete",
            "failed": END,
        },
    )

    workflow.add_edge("complete", END)

    return workflow


def create_workflow_app_v2(llm_handler=None) -> object:
    """创建并编译 V2 工作流应用"""
    graph = build_workflow_graph_v2(llm_handler=llm_handler)
    return graph.compile()
