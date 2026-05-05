"""LangGraph 工作流图定义

定义工作流状态机的节点和边，实现完整的状态转换流程。
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from pm_workstation.models.core import WorkflowStatus
from pm_workstation.orchestrator.workflow_state import WorkflowState


class WorkflowNodes:
    """工作流节点定义

    每个节点对应一个工作流阶段，执行相应的处理逻辑。
    """

    @staticmethod
    def parsing_node(state: WorkflowState) -> dict:
        """需求解析节点 (PARSING -> PARSED)

        将原始需求文本解析为结构化需求。
        """
        state.update_status(WorkflowStatus.PARSING)

        try:
            # 在实际实现中，这里会调用 RequirementParser
            # 目前模拟解析过程
            if not state.workflow_run.requirement_text:
                raise ValueError("需求文本为空")

            # 如果存在澄清问题，进入等待用户输入
            if state.clarification_questions:
                state.update_status(WorkflowStatus.WAITING_USER_INPUT)
                return {"workflow_run": state.workflow_run, "clarification_questions": state.clarification_questions}

            state.update_status(WorkflowStatus.PARSED)
            return {"workflow_run": state.workflow_run}

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def generating_node(state: WorkflowState) -> dict:
        """原型与文档生成节点 (PARSED -> GENERATING -> GENERATED)

        并行生成原型和 PRD 文档。
        """
        state.update_status(WorkflowStatus.GENERATING)

        try:
            # 检查是否有结构化需求
            if not state.structured_requirement and not state.workflow_run.structured_requirement:
                raise ValueError("缺少结构化需求，无法生成")

            # 在实际实现中，这里会并行调用：
            # - PrototypeGenerator 生成原型
            # - DocumentGenerator 生成 PRD 文档
            # 目前模拟生成过程

            state.update_status(WorkflowStatus.GENERATED)
            return {"workflow_run": state.workflow_run}

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def verifying_node(state: WorkflowState) -> dict:
        """校验节点 (GENERATED -> VERIFYING -> VERIFIED)

        对生成的原型和文档进行校验。
        """
        state.update_status(WorkflowStatus.VERIFYING)

        try:
            # 在实际实现中，这里会调用：
            # - PrototypeVerifier 校验原型
            # - DocumentVerifier 校验文档
            # - ConsistencyChecker 检查一致性
            # - AutoFixer 自动修复可修复问题
            # - IssueReporter 生成报告
            # 目前模拟校验过程

            if state.pause_requested:
                state.update_status(WorkflowStatus.WAITING_USER_INPUT)
                return {"workflow_run": state.workflow_run}

            state.update_status(WorkflowStatus.VERIFIED)
            return {"workflow_run": state.workflow_run}

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def completing_node(state: WorkflowState) -> dict:
        """完成节点 (VERIFIED -> COMPLETED)

        标记工作流完成。
        """
        state.update_status(WorkflowStatus.COMPLETED)
        return {"workflow_run": state.workflow_run}

    @staticmethod
    def handle_user_input_node(state: WorkflowState) -> dict:
        """处理用户输入节点 (WAITING_USER_INPUT -> 恢复)

        处理用户的澄清回复。
        """
        if state.user_responses:
            # 用户已回复，清除等待状态
            state.update_status(WorkflowStatus.PARSING)
            return {"workflow_run": state.workflow_run, "user_responses": []}

        # 仍在等待用户输入
        state.update_status(WorkflowStatus.WAITING_USER_INPUT)
        return {"workflow_run": state.workflow_run}


def should_proceed_to_generate(state: WorkflowState) -> Literal["generate", "wait_for_user"]:
    """判断是否进入生成阶段

    如果解析阶段产生了澄清问题且用户尚未回复，等待用户输入。
    """
    if state.clarification_questions and not state.user_responses:
        return "wait_for_user"
    return "generate"


def should_proceed_to_complete(state: WorkflowState) -> Literal["complete", "failed"]:
    """判断是否进入完成阶段

    如果校验通过，进入完成阶段；否则标记失败。
    """
    if state.error_message:
        return "failed"
    if state.workflow_run.status == WorkflowStatus.VERIFIED:
        return "complete"
    return "failed"


def should_handle_pause(state: WorkflowState) -> Literal["pause", "continue"]:
    """判断是否需要暂停

    如果用户请求暂停，进入等待状态。
    """
    if state.pause_requested:
        return "pause"
    return "continue"


def build_workflow_graph() -> StateGraph:
    """构建工作流图

    定义完整的状态转换流程：
    INIT -> PARSING -> PARSED -> GENERATING -> GENERATED -> VERIFYING -> VERIFIED -> COMPLETED

    异常路径：
    - 任何阶段 -> FAILED
    - PARSING -> WAITING_USER_INPUT -> PARSING（循环）
    """
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("parse", WorkflowNodes.parsing_node)
    workflow.add_node("generate", WorkflowNodes.generating_node)
    workflow.add_node("verify", WorkflowNodes.verifying_node)
    workflow.add_node("complete", WorkflowNodes.completing_node)
    workflow.add_node("handle_user_input", WorkflowNodes.handle_user_input_node)

    # 定义边
    workflow.add_edge(START, "parse")

    # PARSING 后的条件路由
    workflow.add_conditional_edges(
        "parse",
        should_proceed_to_generate,
        {
            "generate": "generate",
            "wait_for_user": "handle_user_input",
        },
    )

    # 用户输入处理后的路由
    workflow.add_edge("handle_user_input", "parse")

    # GENERATING -> GENERATED 后进入 VERIFYING
    workflow.add_conditional_edges(
        "generate",
        should_handle_pause,
        {
            "pause": "handle_user_input",
            "continue": "verify",
        },
    )

    # VERIFYING 后的条件路由
    workflow.add_conditional_edges(
        "verify",
        should_proceed_to_complete,
        {
            "complete": "complete",
            "failed": END,
        },
    )

    # 完成后结束
    workflow.add_edge("complete", END)

    return workflow


def create_workflow_app() -> object:
    """创建并编译工作流应用

    Returns:
        编译后的 LangGraph 应用
    """
    graph = build_workflow_graph()
    return graph.compile()
