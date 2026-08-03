"""Sandbox 工具管理器

管理所有工具的注册、验证和执行。
"""

import logging
from collections.abc import Callable

from pm_workstation.sandbox.models import (
    ExecutionContext,
    ToolCategory,
    ToolDefinition,
    ToolResult,
    Workspace,
)
from pm_workstation.sandbox.tools.file_tools import FileTools, get_file_tools
from pm_workstation.sandbox.tools.http_tools import HTTPTools, get_http_tools
from pm_workstation.sandbox.tools.python_tools import PythonTools, get_python_tools
from pm_workstation.sandbox.tools.shell_tools import ShellTools, get_shell_tools

FILE_TOOLS = FileTools.TOOLS
SHELL_TOOLS = ShellTools.TOOLS
PYTHON_TOOLS = PythonTools.TOOLS
HTTP_TOOLS = HTTPTools.TOOLS

logger = logging.getLogger(__name__)


class ToolManager:
    """工具管理器

    管理所有工具的：
    - 注册
    - 验证参数
    - 执行
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._executors: dict[str, Callable] = {}

        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        file_tools = get_file_tools()
        for tool in FILE_TOOLS:
            self.register_tool(tool, self._get_file_executor(tool.name, file_tools))

        shell_tools = get_shell_tools()
        for tool in SHELL_TOOLS:
            self.register_tool(tool, self._get_shell_executor(tool.name, shell_tools))

        python_tools = get_python_tools()
        for tool in PYTHON_TOOLS:
            self.register_tool(tool, self._get_python_executor(tool.name, python_tools))

        http_tools = get_http_tools()
        for tool in HTTP_TOOLS:
            self.register_tool(tool, self._get_http_executor(tool.name, http_tools))

        logger.info(f"Registered {len(self._tools)} builtin tools")

    def register_tool(
        self,
        tool: ToolDefinition,
        executor: Callable,
    ) -> None:
        """注册工具

        Args:
            tool: 工具定义
            executor: 执行函数
        """
        self._tools[tool.name] = tool
        self._executors[tool.name] = executor

        logger.debug(f"Registered tool: {tool.name}")

    def unregister_tool(
        self,
        name: str,
    ) -> bool:
        """注销工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功
        """
        if name in self._tools:
            self._tools.pop(name)
            self._executors.pop(name)
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False

    def get_tool(
        self,
        name: str,
    ) -> ToolDefinition | None:
        """获取工具定义

        Args:
            name: 工具名称

        Returns:
            Optional[ToolDefinition]: 工具定义
        """
        return self._tools.get(name)

    def list_tools(
        self,
        category: ToolCategory | None = None,
    ) -> list[ToolDefinition]:
        """列出工具

        Args:
            category: 工具类别过滤

        Returns:
            list[ToolDefinition]: 工具列表
        """
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def validate_params(
        self,
        tool: ToolDefinition,
        params: dict,
    ) -> tuple[bool, str | None]:
        """验证工具参数

        Args:
            tool: 工具定义
            params: 参数

        Returns:
            tuple: (是否有效, 错误信息)
        """
        schema = tool.parameters

        if not schema:
            return True, None

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for req in required:
            if req not in params:
                return False, f"Missing required parameter: {req}"

        for key, value in params.items():
            if key not in properties:
                continue

            prop_schema = properties[key]
            expected_type = prop_schema.get("type")

            if expected_type == "string" and not isinstance(value, str):
                return False, f"Parameter {key} should be string"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"Parameter {key} should be integer"
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False, f"Parameter {key} should be boolean"
            elif expected_type == "array" and not isinstance(value, list):
                return False, f"Parameter {key} should be array"
            elif expected_type == "object" and not isinstance(value, dict):
                return False, f"Parameter {key} should be object"

        return True, None

    async def execute_tool(
        self,
        tool_name: str,
        workspace: Workspace,
        params: dict,
        context: ExecutionContext | None = None,
    ) -> ToolResult:
        """执行工具

        Args:
            tool_name: 工具名称
            workspace: 工作区
            params: 参数
            context: 执行上下文

        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)

        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        valid, error = self.validate_params(tool, params)
        if not valid:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=error,
            )

        executor = self._executors.get(tool_name)
        if not executor:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"No executor for tool: {tool_name}",
            )

        try:
            result = await executor(workspace, params)

            if context:
                context.tool_results.append(result)

            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
            )

    def _get_file_executor(
        self,
        name: str,
        file_tools: FileTools,
    ) -> Callable:
        """获取文件工具执行器"""
        executors = {
            "file_read": file_tools.read_file,
            "file_write": file_tools.write_file,
            "file_list": file_tools.list_files,
            "file_delete": file_tools.delete_file,
            "file_copy": file_tools.copy_file,
            "file_move": file_tools.move_file,
        }
        return executors.get(name)

    def _get_shell_executor(
        self,
        name: str,
        shell_tools: ShellTools,
    ) -> Callable:
        """获取 Shell 工具执行器"""
        executors = {
            "shell_execute": shell_tools.execute,
            "shell_script": shell_tools.execute_script,
        }
        return executors.get(name)

    def _get_python_executor(
        self,
        name: str,
        python_tools: PythonTools,
    ) -> Callable:
        """获取 Python 工具执行器"""
        executors = {
            "python_execute": python_tools.execute,
            "python_script": python_tools.execute_script,
        }
        return executors.get(name)

    def _get_http_executor(
        self,
        name: str,
        http_tools: HTTPTools,
    ) -> Callable:
        """获取 HTTP 工具执行器"""
        executors = {
            "http_get": http_tools.get,
            "http_post": http_tools.post,
        }
        return executors.get(name)


_global_tool_manager: ToolManager | None = None


def get_tool_manager() -> ToolManager:
    """获取全局工具管理器实例"""
    global _global_tool_manager
    if _global_tool_manager is None:
        _global_tool_manager = ToolManager()
    return _global_tool_manager
