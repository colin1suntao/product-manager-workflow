"""Shell 执行工具

提供 Shell 命令执行能力。
"""

import logging
import time
from typing import Optional

from pm_workstation.sandbox.models import (
    ToolCategory,
    ToolDefinition,
    ToolResult,
    Workspace,
)
from pm_workstation.sandbox.security_controller import (
    SecurityController,
    get_security_controller,
)
from pm_workstation.sandbox.process_executor import (
    ProcessExecutor,
    get_process_executor,
)

logger = logging.getLogger(__name__)


class ShellTools:
    """Shell 执行工具集合"""
    
    TOOLS = [
        ToolDefinition(
            name="shell_execute",
            description="执行 Shell 命令",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell 命令"},
                    "timeout": {"type": "integer", "description": "超时时间（秒）"},
                },
                "required": ["command"],
            },
            returns={
                "type": "object",
                "properties": {
                    "exit_code": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                },
            },
            timeout=30,
            category=ToolCategory.SHELL,
        ),
        ToolDefinition(
            name="shell_script",
            description="执行脚本文件",
            parameters={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "脚本文件路径"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "interpreter": {"type": "string"},
                },
                "required": ["script_path"],
            },
            returns={
                "type": "object",
                "properties": {
                    "exit_code": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                },
            },
            timeout=60,
            category=ToolCategory.SHELL,
        ),
    ]
    
    def __init__(
        self,
        process_executor: Optional[ProcessExecutor] = None,
        security_controller: Optional[SecurityController] = None,
    ):
        self.process_executor = process_executor or get_process_executor()
        self.security_controller = security_controller or get_security_controller()
    
    async def execute(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """执行 Shell 命令"""
        start_time = time.time()
        
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        
        validation = self.security_controller.validate_command(command)
        if not validation.valid:
            return ToolResult(
                tool_name="shell_execute",
                success=False,
                error=f"Command blocked: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        try:
            result = await self.process_executor.execute_shell(
                command=command,
                workspace=workspace,
                timeout=timeout,
            )
            
            success = result.exit_code == 0
            
            output = f"Exit code: {result.exit_code}\n"
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Error:\n{result.stderr}\n"
            
            return ToolResult(
                tool_name="shell_execute",
                success=success,
                output=output,
                error=result.stderr if not success else None,
                metadata={
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "timed_out": result.timed_out,
                },
                execution_time_ms=result.execution_time_ms,
            )
        except Exception as e:
            logger.error(f"shell_execute failed: {e}")
            return ToolResult(
                tool_name="shell_execute",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    async def execute_script(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """执行脚本文件"""
        start_time = time.time()
        
        script_path = params.get("script_path", "")
        args = params.get("args", [])
        interpreter = params.get("interpreter")
        
        try:
            result = await self.process_executor.execute_script(
                script_path=script_path,
                workspace=workspace,
                args=args,
                interpreter=interpreter,
            )
            
            success = result.exit_code == 0
            
            return ToolResult(
                tool_name="shell_script",
                success=success,
                output=f"Exit code: {result.exit_code}\nOutput: {result.stdout}",
                error=result.stderr if not success else None,
                metadata={
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                execution_time_ms=result.execution_time_ms,
            )
        except Exception as e:
            logger.error(f"shell_script failed: {e}")
            return ToolResult(
                tool_name="shell_script",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


_global_shell_tools: Optional[ShellTools] = None


def get_shell_tools() -> ShellTools:
    """获取全局 Shell 工具实例"""
    global _global_shell_tools
    if _global_shell_tools is None:
        _global_shell_tools = ShellTools()
    return _global_shell_tools