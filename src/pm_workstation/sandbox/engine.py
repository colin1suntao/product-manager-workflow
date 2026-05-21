"""Sandbox 执行引擎

管理执行上下文、协调工具调用、收集产物。
"""

import datetime
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from pm_workstation.sandbox.models import (
    ExecutionContext,
    ExecutionEvent,
    ExecutionStatus,
    ExecutionSummary,
    ResourceLimits,
    ToolCall,
    ToolResult,
)
from pm_workstation.sandbox.resource_monitor import ResourceMonitor, get_resource_monitor
from pm_workstation.sandbox.security_controller import SecurityController, get_security_controller
from pm_workstation.sandbox.tool_manager import ToolManager, get_tool_manager
from pm_workstation.sandbox.workspace_manager import WorkspaceManager, get_workspace_manager

logger = logging.getLogger(__name__)


class SandboxEngine:
    """Sandbox 执行引擎
    
    核心功能：
    - 创建执行上下文
    - 协调工具调用
    - 监控资源使用
    - 收集产物
    - 流式事件推送
    """

    DEFAULT_TIMEOUT = 60
    DEFAULT_RESOURCE_LIMITS = ResourceLimits()

    def __init__(
        self,
        tool_manager: ToolManager | None = None,
        workspace_manager: WorkspaceManager | None = None,
        resource_monitor: ResourceMonitor | None = None,
        security_controller: SecurityController | None = None,
    ):
        self.tool_manager = tool_manager or get_tool_manager()
        self.workspace_manager = workspace_manager or get_workspace_manager()
        self.resource_monitor = resource_monitor or get_resource_monitor()
        self.security_controller = security_controller or get_security_controller()

        self._active_executions: dict[str, ExecutionContext] = {}

    def create_execution(
        self,
        task_params: dict,
        timeout: int = None,
        resource_limits: ResourceLimits | None = None,
        session_id: str | None = None,
        workflow_id: str | None = None,
    ) -> ExecutionContext:
        """创建执行上下文
        
        Args:
            task_params: 任务参数
            timeout: 超时时间
            resource_limits: 资源限制
            session_id: 会话 ID
            workflow_id: 工作流 ID
            
        Returns:
            ExecutionContext: 执行上下文
        """
        execution_id = f"sandbox-{uuid.uuid4().hex[:12]}"

        workspace = self.workspace_manager.create_workspace(
            execution_id=execution_id,
            session_id=session_id,
            workflow_id=workflow_id,
        )

        context = ExecutionContext(
            execution_id=execution_id,
            workspace_path=workspace.path,
            task_params=task_params,
            created_at=datetime.datetime.now(),
            timeout=timeout or self.DEFAULT_TIMEOUT,
            resource_limits=resource_limits or self.DEFAULT_RESOURCE_LIMITS,
            status=ExecutionStatus.CREATED,
        )

        self._active_executions[execution_id] = context

        self.resource_monitor.start_monitoring(context, context.resource_limits)

        logger.info(f"Created execution: {execution_id}")

        return context

    async def invoke_tool(
        self,
        context: ExecutionContext,
        tool_name: str,
        params: dict,
    ) -> ToolResult:
        """调用工具
        
        Args:
            context: 执行上下文
            tool_name: 工具名称
            params: 参数
            
        Returns:
            ToolResult: 执行结果
        """
        context.status = ExecutionStatus.RUNNING

        workspace = self.workspace_manager.create_workspace(context.execution_id)

        result = await self.tool_manager.execute_tool(
            tool_name=tool_name,
            workspace=workspace,
            params=params,
            context=context,
        )

        exceeded, reason = self.resource_monitor.check_limits(
            context,
            context.resource_limits,
        )

        if exceeded:
            context.status = ExecutionStatus.FAILED
            context.error_message = reason
            logger.warning(f"Resource exceeded for {context.execution_id}: {reason}")

        return result

    async def execute_streaming(
        self,
        context: ExecutionContext,
        tool_calls: list[ToolCall],
    ) -> AsyncGenerator[dict, None]:
        """流式执行多个工具调用
        
        Args:
            context: 执行上下文
            tool_calls: 工具调用列表
            
        Yields:
            dict: 执行事件
        """
        context.status = ExecutionStatus.RUNNING

        yield self._make_event(
            ExecutionEvent.EXECUTION_STARTED,
            {
                "execution_id": context.execution_id,
                "tool_calls_count": len(tool_calls),
            }
        )

        workspace = self.workspace_manager.create_workspace(context.execution_id)

        for tool_call in tool_calls:
            yield self._make_event(
                ExecutionEvent.TOOL_STARTED,
                {
                    "tool_name": tool_call.name,
                    "params": tool_call.params,
                }
            )

            try:
                result = await self.tool_manager.execute_tool(
                    tool_name=tool_call.name,
                    workspace=workspace,
                    params=tool_call.params,
                    context=context,
                )

                if result.success:
                    yield self._make_event(
                        ExecutionEvent.TOOL_COMPLETED,
                        {
                            "tool_name": result.tool_name,
                            "output": result.output,
                            "files_created": result.files_created,
                            "execution_time_ms": result.execution_time_ms,
                        }
                    )

                    for file in result.files_created:
                        yield self._make_event(
                            ExecutionEvent.FILE_CREATED,
                            {"file_path": file}
                        )
                else:
                    yield self._make_event(
                        ExecutionEvent.TOOL_FAILED,
                        {
                            "tool_name": result.tool_name,
                            "error": result.error,
                        }
                    )

            except Exception as e:
                logger.error(f"Tool execution failed: {tool_call.name} - {e}")
                yield self._make_event(
                    ExecutionEvent.TOOL_FAILED,
                    {
                        "tool_name": tool_call.name,
                        "error": str(e),
                    }
                )

            exceeded, reason = self.resource_monitor.check_limits(
                context,
                context.resource_limits,
            )

            if exceeded:
                yield self._make_event(
                    ExecutionEvent.RESOURCE_WARNING,
                    {"reason": reason}
                )
                break

        summary = self.finalize_execution(context)

        yield self._make_event(
            ExecutionEvent.EXECUTION_COMPLETED,
            summary.model_dump()
        )

    def finalize_execution(
        self,
        context: ExecutionContext,
    ) -> ExecutionSummary:
        """结束执行，收集产物
        
        Args:
            context: 执行上下文
            
        Returns:
            ExecutionSummary: 执行摘要
        """
        workspace = self.workspace_manager.create_workspace(context.execution_id)

        artifacts = self.workspace_manager.get_artifacts(workspace)
        context.artifacts = artifacts

        resource_usage = self.resource_monitor.stop_monitoring(context)

        successful_tools = sum(1 for r in context.tool_results if r.success)
        failed_tools = len(context.tool_results) - successful_tools

        total_execution_time_ms = sum(
            r.execution_time_ms for r in context.tool_results
        )

        if context.error_message:
            context.status = ExecutionStatus.FAILED
        elif failed_tools > 0 and successful_tools == 0:
            context.status = ExecutionStatus.FAILED
        else:
            context.status = ExecutionStatus.COMPLETED

        summary = ExecutionSummary(
            execution_id=context.execution_id,
            status=context.status,
            total_tools_called=len(context.tool_results),
            successful_tools=successful_tools,
            failed_tools=failed_tools,
            artifacts_count=len(artifacts),
            total_execution_time_ms=total_execution_time_ms,
            resource_usage=resource_usage,
            error_message=context.error_message,
        )

        self._active_executions.pop(context.execution_id, None)

        logger.info(f"Finalized execution: {context.execution_id} - {context.status}")

        return summary

    def get_execution_status(
        self,
        execution_id: str,
    ) -> ExecutionContext | None:
        """获取执行状态
        
        Args:
            execution_id: 执行 ID
            
        Returns:
            Optional[ExecutionContext]: 执行上下文
        """
        return self._active_executions.get(execution_id)

    def cancel_execution(
        self,
        execution_id: str,
    ) -> bool:
        """取消执行
        
        Args:
            execution_id: 执行 ID
            
        Returns:
            bool: 是否成功
        """
        context = self._active_executions.get(execution_id)

        if context:
            context.status = ExecutionStatus.CANCELLED
            self.resource_monitor.terminate_execution(context, "User cancelled")

            self.finalize_execution(context)

            return True

        return False

    def cleanup_workspace(
        self,
        execution_id: str,
        preserve_artifacts: bool = True,
    ) -> bool:
        """清理工作区
        
        Args:
            execution_id: 执行 ID
            preserve_artifacts: 是否保留产物
            
        Returns:
            bool: 是否成功
        """
        workspace = self.workspace_manager.create_workspace(execution_id)

        self.workspace_manager.cleanup_workspace(workspace, preserve_artifacts)

        return True

    def _make_event(
        self,
        event_type: ExecutionEvent,
        data: dict,
    ) -> dict:
        """创建事件
        
        Args:
            event_type: 事件类型
            data: 数据
            
        Returns:
            dict: SSE 事件格式
        """
        return {
            "event": event_type.value,
            "data": json.dumps(data),
        }


_global_sandbox_engine: SandboxEngine | None = None


def get_sandbox_engine() -> SandboxEngine:
    """获取全局 Sandbox 引擎实例"""
    global _global_sandbox_engine
    if _global_sandbox_engine is None:
        _global_sandbox_engine = SandboxEngine()
    return _global_sandbox_engine
