"""Sandbox 工作区管理器

管理执行环境的文件系统，包括文件读写、目录管理等。
"""

import datetime
import logging
import os
import shutil
import uuid

from pm_workstation.sandbox.models import (
    FileContent,
    FileInfo,
    Workspace,
)

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """工作区管理器

    管理执行环境的文件系统：
    - 创建/删除工作区
    - 读写文件
    - 列出文件
    - 清理工作区
    """

    DEFAULT_BASE_PATH = "/tmp/sandbox"

    CONTENT_TYPE_MAP = {
        ".html": "text/html",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".csv": "text/csv",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".ts": "text/typescript",
        ".css": "text/css",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }

    def __init__(self, base_path: str = None):
        self.base_path = base_path or self.DEFAULT_BASE_PATH

        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
            logger.info(f"Created sandbox base path: {self.base_path}")

    def create_workspace(
        self,
        execution_id: str,
        session_id: str | None = None,
        workflow_id: str | None = None,
    ) -> Workspace:
        """创建工作区

        Args:
            execution_id: 执行 ID
            session_id: 会话 ID（可选）
            workflow_id: 工作流 ID（可选）

        Returns:
            Workspace: 工作区对象
        """
        workspace_id = f"ws-{uuid.uuid4().hex[:12]}"

        workspace_path = os.path.join(self.base_path, execution_id)

        os.makedirs(workspace_path, exist_ok=True)

        subdirs = ["inputs", "outputs", "temp"]
        for subdir in subdirs:
            os.makedirs(os.path.join(workspace_path, subdir), exist_ok=True)

        workspace = Workspace(
            workspace_id=workspace_id,
            execution_id=execution_id,
            path=workspace_path,
            created_at=datetime.datetime.now(),
            file_count=0,
            total_size_bytes=0,
        )

        logger.info(f"Created workspace: {workspace_id} at {workspace_path}")

        return workspace

    def read_file(
        self,
        workspace: Workspace,
        file_path: str,
    ) -> FileContent:
        """读取文件内容

        Args:
            workspace: 工作区
            file_path: 文件路径（相对路径或绝对路径）

        Returns:
            FileContent: 文件内容

        Raises:
            FileNotFoundError: 文件不存在
        """
        full_path = self._resolve_path(workspace, file_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, encoding="utf-8") as f:
            content = f.read()

        content_type = self._get_content_type(full_path)
        size_bytes = os.path.getsize(full_path)

        return FileContent(
            file_path=file_path,
            content=content,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    def read_file_binary(
        self,
        workspace: Workspace,
        file_path: str,
    ) -> bytes:
        """读取二进制文件

        Args:
            workspace: 工作区
            file_path: 文件路径

        Returns:
            bytes: 文件内容
        """
        full_path = self._resolve_path(workspace, file_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, "rb") as f:
            return f.read()

    def write_file(
        self,
        workspace: Workspace,
        file_path: str,
        content: str,
        content_type: str | None = None,
    ) -> FileInfo:
        """写入文件

        Args:
            workspace: 工作区
            file_path: 文件路径（相对路径）
            content: 文件内容
            content_type: 内容类型（可选）

        Returns:
            FileInfo: 文件信息
        """
        full_path = self._resolve_path(workspace, file_path)

        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        encoding = "utf-8"
        if content_type and content_type.startswith("image/"):
            encoding = None

        if encoding:
            with open(full_path, "w", encoding=encoding) as f:
                f.write(content)
        else:
            with open(full_path, "wb") as f:
                f.write(content.encode("utf-8") if isinstance(content, str) else content)

        if not content_type:
            content_type = self._get_content_type(full_path)

        stat = os.stat(full_path)

        file_info = FileInfo(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            content_type=content_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime),
        )

        logger.debug(f"Written file: {file_path} ({stat.st_size} bytes)")

        return file_info

    def write_file_binary(
        self,
        workspace: Workspace,
        file_path: str,
        content: bytes,
    ) -> FileInfo:
        """写入二进制文件

        Args:
            workspace: 工作区
            file_path: 文件路径
            content: 二进制内容

        Returns:
            FileInfo: 文件信息
        """
        full_path = self._resolve_path(workspace, file_path)

        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        content_type = self._get_content_type(full_path)
        stat = os.stat(full_path)

        return FileInfo(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            content_type=content_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime),
        )

    def list_files(
        self,
        workspace: Workspace,
        directory: str = "",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """列出文件

        Args:
            workspace: 工作区
            directory: 目录路径（相对路径）
            recursive: 是否递归列出

        Returns:
            list[FileInfo]: 文件列表
        """
        base_dir = self._resolve_path(workspace, directory)

        if not os.path.exists(base_dir):
            return []

        files = []

        if recursive:
            for root, dirs, filenames in os.walk(base_dir):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, workspace.path)

                    file_info = self._get_file_info(rel_path, full_path)
                    files.append(file_info)
        else:
            for filename in os.listdir(base_dir):
                full_path = os.path.join(base_dir, filename)
                if os.path.isfile(full_path):
                    rel_path = os.path.relpath(full_path, workspace.path)

                    file_info = self._get_file_info(rel_path, full_path)
                    files.append(file_info)

        return files

    def delete_file(
        self,
        workspace: Workspace,
        file_path: str,
    ) -> bool:
        """删除文件

        Args:
            workspace: 工作区
            file_path: 文件路径

        Returns:
            bool: 是否成功删除
        """
        full_path = self._resolve_path(workspace, file_path)

        if not os.path.exists(full_path):
            return False

        try:
            os.remove(full_path)
            logger.debug(f"Deleted file: {file_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def copy_file(
        self,
        workspace: Workspace,
        source: str,
        target: str,
    ) -> FileInfo:
        """复制文件

        Args:
            workspace: 工作区
            source: 源文件路径
            target: 目标文件路径

        Returns:
            FileInfo: 目标文件信息
        """
        source_path = self._resolve_path(workspace, source)
        target_path = self._resolve_path(workspace, target)

        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source}")

        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        shutil.copy2(source_path, target_path)

        return self._get_file_info(target, target_path)

    def move_file(
        self,
        workspace: Workspace,
        source: str,
        target: str,
    ) -> FileInfo:
        """移动文件

        Args:
            workspace: 工作区
            source: 源文件路径
            target: 目标文件路径

        Returns:
            FileInfo: 目标文件信息
        """
        source_path = self._resolve_path(workspace, source)
        target_path = self._resolve_path(workspace, target)

        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source}")

        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        shutil.move(source_path, target_path)

        return self._get_file_info(target, target_path)

    def cleanup_workspace(
        self,
        workspace: Workspace,
        preserve_artifacts: bool = False,
    ) -> None:
        """清理工作区

        Args:
            workspace: 工作区
            preserve_artifacts: 是否保留产物文件
        """
        workspace_path = workspace.path

        if preserve_artifacts:
            outputs_dir = os.path.join(workspace_path, "outputs")
            if os.path.exists(outputs_dir):
                logger.info(f"Preserving artifacts in {outputs_dir}")
                return

        try:
            shutil.rmtree(workspace_path)
            logger.info(f"Cleaned up workspace: {workspace.workspace_id}")
        except OSError as e:
            logger.error(f"Failed to cleanup workspace: {e}")

    def get_artifacts(
        self,
        workspace: Workspace,
    ) -> list[FileInfo]:
        """获取所有产物文件

        Args:
            workspace: 工作区

        Returns:
            list[FileInfo]: 产物文件列表
        """
        outputs_dir = os.path.join(workspace.path, "outputs")

        if not os.path.exists(outputs_dir):
            return []

        return self.list_files(workspace, "outputs", recursive=True)

    def _resolve_path(
        self,
        workspace: Workspace,
        file_path: str,
    ) -> str:
        """解析文件路径（限制在工作区根目录内）

        Args:
            workspace: 工作区
            file_path: 文件路径

        Returns:
            str: 绝对路径
        """
        workspace_root = os.path.realpath(workspace.path)
        if file_path.startswith(workspace_root):
            candidate = file_path
        else:
            candidate = os.path.join(workspace.path, file_path)

        # 规范化并校验包含关系，防止 .. / 绝对路径逃逸工作区
        resolved = os.path.realpath(candidate)
        if resolved != workspace_root and not resolved.startswith(workspace_root + os.sep):
            raise ValueError(f"Path escapes workspace root: {file_path}")

        return resolved

    def _get_content_type(
        self,
        file_path: str,
    ) -> str:
        """获取文件内容类型

        Args:
            file_path: 文件路径

        Returns:
            str: 内容类型
        """
        ext = os.path.splitext(file_path)[1].lower()
        return self.CONTENT_TYPE_MAP.get(ext, "text/plain")

    def _get_file_info(
        self,
        rel_path: str,
        full_path: str,
    ) -> FileInfo:
        """获取文件信息

        Args:
            rel_path: 相对路径
            full_path: 绝对路径

        Returns:
            FileInfo: 文件信息
        """
        stat = os.stat(full_path)

        return FileInfo(
            file_path=rel_path,
            file_name=os.path.basename(full_path),
            content_type=self._get_content_type(full_path),
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime),
        )


_global_workspace_manager: WorkspaceManager | None = None


def get_workspace_manager() -> WorkspaceManager:
    """获取全局工作区管理器实例"""
    global _global_workspace_manager
    if _global_workspace_manager is None:
        _global_workspace_manager = WorkspaceManager()
    return _global_workspace_manager
