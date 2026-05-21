"""Python 执行工具

提供 Python 代码执行能力。
"""

import json
import logging
import time
from typing import Any, Optional

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


class PythonTools:
    """Python 执行工具集合"""
    
    TOOLS = [
        ToolDefinition(
            name="python_execute",
            description="执行 Python 代码",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python 代码"},
                    "input_data": {"type": "object", "description": "输入数据"},
                    "imports": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "description": "超时时间（秒）"},
                },
                "required": ["code"],
            },
            returns={
                "type": "object",
                "properties": {
                    "stdout": {"type": "string"},
                    "return_value": {"type": "any"},
                    "files": {"type": "array"},
                },
            },
            timeout=60,
            category=ToolCategory.PYTHON,
        ),
        ToolDefinition(
            name="python_script",
            description="执行 Python 脚本文件",
            parameters={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "脚本文件路径"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "input_data": {"type": "object"},
                },
                "required": ["script_path"],
            },
            returns={
                "type": "object",
                "properties": {
                    "stdout": {"type": "string"},
                    "files": {"type": "array"},
                },
            },
            timeout=60,
            category=ToolCategory.PYTHON,
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
        """执行 Python 代码"""
        start_time = time.time()
        
        code = params.get("code", "")
        input_data = params.get("input_data")
        imports = params.get("imports", [])
        timeout = params.get("timeout", 60)
        
        validation = self.security_controller.validate_python_code(code)
        if not validation.valid:
            return ToolResult(
                tool_name="python_execute",
                success=False,
                error=f"Code blocked: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        try:
            result = await self.process_executor.execute_python(
                code=code,
                workspace=workspace,
                timeout=timeout,
                input_data=input_data,
                imports=imports,
            )
            
            success = not result.exception and not result.stderr
            
            output = f"Output:\n{result.stdout}\n"
            if result.return_value:
                output += f"Return value: {json.dumps(result.return_value)}\n"
            if result.files_created:
                output += f"Files created: {result.files_created}\n"
            
            return ToolResult(
                tool_name="python_execute",
                success=success,
                output=output,
                error=result.exception or result.stderr if not success else None,
                files_created=result.files_created,
                metadata={
                    "stdout": result.stdout,
                    "return_value": result.return_value,
                    "files_created": result.files_created,
                },
                execution_time_ms=result.execution_time_ms,
            )
        except Exception as e:
            logger.error(f"python_execute failed: {e}")
            return ToolResult(
                tool_name="python_execute",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    async def execute_script(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """执行 Python 脚本"""
        start_time = time.time()
        
        script_path = params.get("script_path", "")
        args = params.get("args", [])
        
        try:
            result = await self.process_executor.execute_script(
                script_path=script_path,
                workspace=workspace,
                args=args,
                interpreter=None,
            )
            
            success = result.exit_code == 0
            
            return ToolResult(
                tool_name="python_script",
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
            logger.error(f"python_script failed: {e}")
            return ToolResult(
                tool_name="python_script",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


_global_python_tools: Optional[PythonTools] = None


def get_python_tools() -> PythonTools:
    """获取全局 Python 工具实例"""
    global _global_python_tools
    if _global_python_tools is None:
        _global_python_tools = PythonTools()
    return _global_python_tools