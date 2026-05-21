"""文件操作工具

提供文件读写、列表、复制、移动等操作。
"""

import logging
import time

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
from pm_workstation.sandbox.workspace_manager import (
    WorkspaceManager,
    get_workspace_manager,
)

logger = logging.getLogger(__name__)


class FileTools:
    """文件操作工具集合"""

    TOOLS = [
        ToolDefinition(
            name="file_read",
            description="读取文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                },
                "required": ["path"],
            },
            returns={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "size": {"type": "integer"},
                },
            },
            timeout=10,
            category=ToolCategory.FILE,
        ),
        ToolDefinition(
            name="file_write",
            description="写入文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "content_type": {"type": "string", "description": "内容类型"},
                },
                "required": ["path", "content"],
            },
            returns={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "size": {"type": "integer"},
                },
            },
            timeout=10,
            category=ToolCategory.FILE,
        ),
        ToolDefinition(
            name="file_list",
            description="列出目录文件",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "目录路径"},
                    "recursive": {"type": "boolean", "description": "是否递归"},
                },
                "required": [],
            },
            returns={
                "type": "array",
                "items": {"type": "object"},
            },
            timeout=5,
            category=ToolCategory.FILE,
        ),
        ToolDefinition(
            name="file_delete",
            description="删除文件",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                },
                "required": ["path"],
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                },
            },
            timeout=5,
            category=ToolCategory.FILE,
        ),
        ToolDefinition(
            name="file_copy",
            description="复制文件",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "源文件路径"},
                    "target": {"type": "string", "description": "目标文件路径"},
                },
                "required": ["source", "target"],
            },
            returns={
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "size": {"type": "integer"},
                },
            },
            timeout=10,
            category=ToolCategory.FILE,
        ),
        ToolDefinition(
            name="file_move",
            description="移动文件",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "源文件路径"},
                    "target": {"type": "string", "description": "目标文件路径"},
                },
                "required": ["source", "target"],
            },
            returns={
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "size": {"type": "integer"},
                },
            },
            timeout=10,
            category=ToolCategory.FILE,
        ),
    ]

    def __init__(
        self,
        workspace_manager: WorkspaceManager | None = None,
        security_controller: SecurityController | None = None,
    ):
        self.workspace_manager = workspace_manager or get_workspace_manager()
        self.security_controller = security_controller or get_security_controller()

    async def read_file(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """读取文件"""
        start_time = time.time()

        path = params.get("path", "")

        validation = self.security_controller.validate_file_path(path, workspace)
        if not validation.valid:
            return ToolResult(
                tool_name="file_read",
                success=False,
                error=f"Path validation failed: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            content = self.workspace_manager.read_file(workspace, path)

            return ToolResult(
                tool_name="file_read",
                success=True,
                output=content.content,
                metadata={
                    "size": content.size_bytes,
                    "content_type": content.content_type,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except FileNotFoundError as e:
            return ToolResult(
                tool_name="file_read",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_read failed: {e}")
            return ToolResult(
                tool_name="file_read",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def write_file(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """写入文件"""
        start_time = time.time()

        path = params.get("path", "")
        content = params.get("content", "")
        content_type = params.get("content_type")

        validation = self.security_controller.validate_file_path(path, workspace)
        if not validation.valid:
            return ToolResult(
                tool_name="file_write",
                success=False,
                error=f"Path validation failed: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            file_info = self.workspace_manager.write_file(
                workspace,
                path,
                content,
                content_type,
            )

            return ToolResult(
                tool_name="file_write",
                success=True,
                output=f"File written: {file_info.file_path} ({file_info.size_bytes} bytes)",
                files_created=[file_info.file_path],
                metadata={
                    "file_path": file_info.file_path,
                    "size": file_info.size_bytes,
                    "content_type": file_info.content_type,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_write failed: {e}")
            return ToolResult(
                tool_name="file_write",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def list_files(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """列出文件"""
        start_time = time.time()

        directory = params.get("directory", "")
        recursive = params.get("recursive", False)

        validation = self.security_controller.validate_file_path(directory or ".", workspace)
        if not validation.valid:
            return ToolResult(
                tool_name="file_list",
                success=False,
                error=f"Path validation failed: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            files = self.workspace_manager.list_files(workspace, directory, recursive)

            file_list_str = "\n".join([
                f"{f.file_name} ({f.size_bytes} bytes, {f.content_type})"
                for f in files
            ])

            return ToolResult(
                tool_name="file_list",
                success=True,
                output=file_list_str,
                metadata={
                    "files": [
                        {
                            "path": f.file_path,
                            "name": f.file_name,
                            "size": f.size_bytes,
                            "content_type": f.content_type,
                        }
                        for f in files
                    ],
                    "total": len(files),
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_list failed: {e}")
            return ToolResult(
                tool_name="file_list",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def delete_file(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """删除文件"""
        start_time = time.time()

        path = params.get("path", "")

        validation = self.security_controller.validate_file_path(path, workspace)
        if not validation.valid:
            return ToolResult(
                tool_name="file_delete",
                success=False,
                error=f"Path validation failed: {validation.reason}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            success = self.workspace_manager.delete_file(workspace, path)

            return ToolResult(
                tool_name="file_delete",
                success=success,
                output=f"File deleted: {path}" if success else f"File not found: {path}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_delete failed: {e}")
            return ToolResult(
                tool_name="file_delete",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def copy_file(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """复制文件"""
        start_time = time.time()

        source = params.get("source", "")
        target = params.get("target", "")

        validation_source = self.security_controller.validate_file_path(source, workspace)
        validation_target = self.security_controller.validate_file_path(target, workspace)

        if not validation_source.valid or not validation_target.valid:
            return ToolResult(
                tool_name="file_copy",
                success=False,
                error="Path validation failed",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            file_info = self.workspace_manager.copy_file(workspace, source, target)

            return ToolResult(
                tool_name="file_copy",
                success=True,
                output=f"File copied: {source} -> {target}",
                files_created=[file_info.file_path],
                metadata={
                    "target_path": file_info.file_path,
                    "size": file_info.size_bytes,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except FileNotFoundError as e:
            return ToolResult(
                tool_name="file_copy",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_copy failed: {e}")
            return ToolResult(
                tool_name="file_copy",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def move_file(
        self,
        workspace: Workspace,
        params: dict,
    ) -> ToolResult:
        """移动文件"""
        start_time = time.time()

        source = params.get("source", "")
        target = params.get("target", "")

        validation_source = self.security_controller.validate_file_path(source, workspace)
        validation_target = self.security_controller.validate_file_path(target, workspace)

        if not validation_source.valid or not validation_target.valid:
            return ToolResult(
                tool_name="file_move",
                success=False,
                error="Path validation failed",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            file_info = self.workspace_manager.move_file(workspace, source, target)

            return ToolResult(
                tool_name="file_move",
                success=True,
                output=f"File moved: {source} -> {target}",
                files_modified=[file_info.file_path],
                metadata={
                    "target_path": file_info.file_path,
                    "size": file_info.size_bytes,
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except FileNotFoundError as e:
            return ToolResult(
                tool_name="file_move",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"file_move failed: {e}")
            return ToolResult(
                tool_name="file_move",
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


_global_file_tools: FileTools | None = None


def get_file_tools() -> FileTools:
    """获取全局文件工具实例"""
    global _global_file_tools
    if _global_file_tools is None:
        _global_file_tools = FileTools()
    return _global_file_tools
