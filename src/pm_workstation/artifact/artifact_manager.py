"""Artifact Manager - 产物管理器

支持产物的：
- 创建和管理
- 版本迭代
- 内容对比
- 搜索和过滤
"""

import difflib
import json
import logging
import os
import uuid
from datetime import datetime

from .artifact_models import (
    Artifact,
    ArtifactDiff,
    ArtifactStatus,
    ArtifactType,
    ArtifactVersion,
)

logger = logging.getLogger(__name__)


class ArtifactManager:
    """产物管理器
    
    管理产物的生命周期，包括：
    - 创建新产物
    - 更新版本
    - 版本对比
    - 搜索和过滤
    - 导出和分享
    """

    def __init__(self, storage_path: str = "/tmp/artifacts"):
        """初始化管理器
        
        Args:
            storage_path: 产物存储目录
        """
        self.storage_path = storage_path
        self.metadata_path = os.path.join(storage_path, "metadata")
        self.content_path = os.path.join(storage_path, "content")

        # 创建存储目录
        os.makedirs(self.metadata_path, exist_ok=True)
        os.makedirs(self.content_path, exist_ok=True)

        # 内存缓存
        self._artifacts_cache: dict[str, Artifact] = {}

        logger.info(f"ArtifactManager initialized with storage: {storage_path}")

    def _generate_artifact_id(self) -> str:
        """生成产物 ID"""
        return f"artifact-{uuid.uuid4().hex[:12]}"

    def _generate_version_id(self, artifact_id: str, version_number: int) -> str:
        """生成版本 ID"""
        return f"{artifact_id}-v{version_number}"

    def _get_metadata_path(self, artifact_id: str) -> str:
        """获取产物元数据文件路径"""
        return os.path.join(self.metadata_path, f"{artifact_id}.json")

    def _get_content_path(self, artifact_id: str, version_number: int) -> str:
        """获取产物内容文件路径"""
        return os.path.join(
            self.content_path,
            artifact_id,
            f"v{version_number}.txt"
        )

    def _save_artifact(self, artifact: Artifact) -> None:
        """保存产物元数据
        
        Args:
            artifact: 产物对象
        """
        path = self._get_metadata_path(artifact.artifact_id)

        # 更新缓存
        self._artifacts_cache[artifact.artifact_id] = artifact

        # 保存到文件
        with open(path, "w", encoding="utf-8") as f:
            json.dump(artifact.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        logger.debug(f"Saved artifact metadata: {artifact.artifact_id}")

    def _save_content(self, artifact_id: str, version_number: int, content: str) -> None:
        """保存产物内容
        
        Args:
            artifact_id: 产物 ID
            version_number: 版本号
            content: 内容
        """
        # 创建产物内容目录
        artifact_content_dir = os.path.join(self.content_path, artifact_id)
        os.makedirs(artifact_content_dir, exist_ok=True)

        path = self._get_content_path(artifact_id, version_number)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Saved artifact content: {artifact_id}-v{version_number}")

    def _load_artifact(self, artifact_id: str) -> Artifact | None:
        """加载产物
        
        Args:
            artifact_id: 产物 ID
        
        Returns:
            产物对象，如果不存在返回 None
        """
        # 先检查缓存
        if artifact_id in self._artifacts_cache:
            return self._artifacts_cache[artifact_id]

        # 从文件加载
        path = self._get_metadata_path(artifact_id)
        if not os.path.exists(path):
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        artifact = Artifact.model_validate(data)
        self._artifacts_cache[artifact_id] = artifact

        return artifact

    def _load_content(self, artifact_id: str, version_number: int) -> str | None:
        """加载产物内容
        
        Args:
            artifact_id: 产物 ID
            version_number: 版本号
        
        Returns:
            内容，如果不存在返回 None
        """
        path = self._get_content_path(artifact_id, version_number)
        if not os.path.exists(path):
            return None

        with open(path, encoding="utf-8") as f:
            return f.read()

    def _compute_diff(
        self,
        content_from: str,
        content_to: str,
    ) -> tuple[str, dict]:
        """计算内容差异
        
        Args:
            content_from: 原内容
            content_to: 新内容
        
        Returns:
            (差异摘要, 详细差异统计)
        """
        lines_from = content_from.splitlines(keepends=True)
        lines_to = content_to.splitlines(keepends=True)

        # 使用 difflib 计算差异
        diff = difflib.unified_diff(
            lines_from,
            lines_to,
            fromfile="previous",
            tofile="current",
        )

        diff_content = "".join(diff)

        # 统计差异
        additions = 0
        deletions = 0
        modifications = 0

        for line in diff_content.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        # 计算相似度
        similarity = difflib.SequenceMatcher(None, content_from, content_to).ratio()

        return diff_content, {
            "additions": additions,
            "deletions": deletions,
            "similarity": round(similarity, 3),
        }

    async def create(
        self,
        name: str,
        type: ArtifactType,
        content: str,
        user_id: str,
        created_by: str,
        created_by_name: str = "",
        session_id: str | None = None,
        workflow_id: str | None = None,
        workflow_execution_id: str | None = None,
        step_id: str | None = None,
        agent_id: str | None = None,
        description: str = "",
        tags: list[str] = [],
    ) -> Artifact:
        """创建新产物
        
        Args:
            name: 产物名称
            type: 产物类型
            content: 内容
            user_id: 用户 ID
            created_by: 创建者 ID (user_id 或 agent_id)
            created_by_name: 创建者名称
            session_id: 会话 ID
            workflow_id: 工作流 ID
            workflow_execution_id: 工作流执行 ID
            step_id: 步骤 ID
            agent_id: 生成 Agent ID
            description: 描述
            tags: 标签
        
        Returns:
            创建的产物对象
        """
        artifact_id = self._generate_artifact_id()
        now = datetime.now()

        # 根据类型确定内容类型
        content_type_map = {
            ArtifactType.PROTOTYPE: "text/html",
            ArtifactType.DOCUMENT: "text/markdown",
            ArtifactType.REPORT: "text/markdown",
            ArtifactType.IMAGE: "image/png",
            ArtifactType.DATA: "application/json",
            ArtifactType.CODE: "text/plain",
            ArtifactType.OTHER: "text/plain",
        }

        # 创建第一个版本
        version = ArtifactVersion(
            version_id=self._generate_version_id(artifact_id, 1),
            version_number=1,
            content=content,
            content_type=content_type_map.get(type, "text/plain"),
            created_at=now,
            created_by=created_by,
            created_by_name=created_by_name,
            size_bytes=len(content.encode("utf-8")),
        )

        # 保存内容
        self._save_content(artifact_id, 1, content)

        # 生成预览 URL
        preview_url = None
        if type == ArtifactType.PROTOTYPE:
            preview_url = f"/artifacts/{artifact_id}/v1/preview"
        elif type in [ArtifactType.DOCUMENT, ArtifactType.REPORT]:
            preview_url = f"/artifacts/{artifact_id}/v1/view"

        # 创建产物
        artifact = Artifact(
            artifact_id=artifact_id,
            name=name,
            type=type,
            status=ArtifactStatus.DRAFT,
            description=description,
            session_id=session_id,
            workflow_id=workflow_id,
            workflow_execution_id=workflow_execution_id,
            step_id=step_id,
            agent_id=agent_id,
            user_id=user_id,
            versions=[version],
            current_version=1,
            tags=tags,
            preview_url=preview_url,
            download_url=f"/artifacts/{artifact_id}/download",
            file_path=self._get_content_path(artifact_id, 1),
            created_at=now,
            updated_at=now,
        )

        # 保存元数据
        self._save_artifact(artifact)

        logger.info(f"Created artifact: {artifact_id} ({name})")

        return artifact

    async def update(
        self,
        artifact_id: str,
        new_content: str,
        created_by: str,
        created_by_name: str = "",
        diff_summary: str | None = None,
    ) -> Artifact:
        """更新产物（创建新版本）
        
        Args:
            artifact_id: 产物 ID
            new_content: 新内容
            created_by: 创建者 ID
            created_by_name: 创建者名称
            diff_summary: 差异摘要（可选）
        
        Returns:
            更新后的产物对象
        
        Raises:
            ValueError: 如果产物不存在
        """
        artifact = self._load_artifact(artifact_id)

        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        if not artifact.is_editable:
            raise ValueError(f"Artifact {artifact_id} is not editable")

        # 获取上一版本内容
        prev_version = artifact.versions[-1]
        prev_content = self._load_content(artifact_id, prev_version.version_number) or prev_version.content

        # 计算差异
        diff_content, diff_stats = self._compute_diff(prev_content, new_content)

        # 创建新版本
        new_version_number = len(artifact.versions) + 1
        new_version = ArtifactVersion(
            version_id=self._generate_version_id(artifact_id, new_version_number),
            version_number=new_version_number,
            content=new_content,
            content_type=prev_version.content_type,
            created_at=datetime.now(),
            created_by=created_by,
            created_by_name=created_by_name,
            diff_summary=diff_summary or f"Changes: +{diff_stats['additions']} -{diff_stats['deletions']}",
            diff_detail=diff_stats,
            size_bytes=len(new_content.encode("utf-8")),
        )

        # 保存新版本内容
        self._save_content(artifact_id, new_version_number, new_content)

        # 更新产物
        artifact.versions.append(new_version)
        artifact.current_version = new_version_number
        artifact.updated_at = datetime.now()
        artifact.file_path = self._get_content_path(artifact_id, new_version_number)

        # 保存元数据
        self._save_artifact(artifact)

        logger.info(f"Updated artifact: {artifact_id} (v{new_version_number})")

        return artifact

    async def get(self, artifact_id: str) -> Artifact | None:
        """获取产物
        
        Args:
            artifact_id: 产物 ID
        
        Returns:
            产物对象，如果不存在返回 None
        """
        return self._load_artifact(artifact_id)

    async def get_version(
        self,
        artifact_id: str,
        version_number: int,
        include_content: bool = True,
    ) -> ArtifactVersion | None:
        """获取指定版本的产物
        
        Args:
            artifact_id: 产物 ID
            version_number: 版本号
            include_content: 是否包含内容
        
        Returns:
            版本对象，如果不存在返回 None
        """
        artifact = self._load_artifact(artifact_id)

        if not artifact:
            return None

        for version in artifact.versions:
            if version.version_number == version_number:
                if include_content:
                    content = self._load_content(artifact_id, version_number)
                    if content:
                        version.content = content
                return version

        return None

    async def get_content(
        self,
        artifact_id: str,
        version_number: int | None = None,
    ) -> str | None:
        """获取产物内容
        
        Args:
            artifact_id: 产物 ID
            version_number: 版本号（可选，默认当前版本）
        
        Returns:
            内容，如果不存在返回 None
        """
        artifact = self._load_artifact(artifact_id)

        if not artifact:
            return None

        version = version_number or artifact.current_version

        return self._load_content(artifact_id, version)

    async def compare_versions(
        self,
        artifact_id: str,
        version_from: int,
        version_to: int,
    ) -> ArtifactDiff | None:
        """对比两个版本
        
        Args:
            artifact_id: 产物 ID
            version_from: 起始版本
            version_to: 目标版本
        
        Returns:
            差异对象
        """
        content_from = self._load_content(artifact_id, version_from)
        content_to = self._load_content(artifact_id, version_to)

        if not content_from or not content_to:
            return None

        diff_content, diff_stats = self._compute_diff(content_from, content_to)

        return ArtifactDiff(
            version_from=version_from,
            version_to=version_to,
            additions=diff_stats["additions"],
            deletions=diff_stats["deletions"],
            similarity=diff_stats["similarity"],
            diff_content=diff_content,
        )

    async def rollback(
        self,
        artifact_id: str,
        target_version: int,
        created_by: str,
        created_by_name: str = "",
    ) -> Artifact:
        """回滚到指定版本
        
        Args:
            artifact_id: 产物 ID
            target_version: 目标版本号
            created_by: 创建者 ID
            created_by_name: 创建者名称
        
        Returns:
            更新后的产物对象
        """
        content = await self.get_content(artifact_id, target_version)

        if not content:
            raise ValueError(f"Version {target_version} content not found")

        return await self.update(
            artifact_id,
            content,
            created_by,
            created_by_name,
            diff_summary=f"Rollback to version {target_version}",
        )

    async def delete(self, artifact_id: str) -> bool:
        """删除产物（标记为已删除）
        
        Args:
            artifact_id: 产物 ID
        
        Returns:
            是否成功删除
        """
        artifact = self._load_artifact(artifact_id)

        if not artifact:
            return False

        artifact.status = ArtifactStatus.DELETED
        artifact.updated_at = datetime.now()

        self._save_artifact(artifact)

        logger.info(f"Deleted artifact: {artifact_id}")

        return True

    async def list_by_user(
        self,
        user_id: str,
        type_filter: ArtifactType | None = None,
        status_filter: ArtifactStatus | None = None,
        limit: int = 50,
    ) -> list[Artifact]:
        """获取用户的产物列表
        
        Args:
            user_id: 用户 ID
            type_filter: 类型过滤（可选）
            status_filter: 状态过滤（可选）
            limit: 最大数量
        
        Returns:
            产物列表
        """
        artifacts = []

        for filename in os.listdir(self.metadata_path):
            if not filename.endswith(".json"):
                continue

            artifact_id = filename[:-5]
            artifact = self._load_artifact(artifact_id)

            if artifact and artifact.user_id == user_id:
                # 过滤条件
                if type_filter and artifact.type != type_filter:
                    continue
                if status_filter and artifact.status != status_filter:
                    continue
                if artifact.status == ArtifactStatus.DELETED:
                    continue

                artifacts.append(artifact)

        # 按更新时间排序
        artifacts.sort(key=lambda a: a.updated_at, reverse=True)

        return artifacts[:limit]

    async def list_by_session(self, session_id: str) -> list[Artifact]:
        """获取会话的产物列表
        
        Args:
            session_id: 会话 ID
        
        Returns:
            产物列表
        """
        artifacts = []

        for filename in os.listdir(self.metadata_path):
            if not filename.endswith(".json"):
                continue

            artifact_id = filename[:-5]
            artifact = self._load_artifact(artifact_id)

            if artifact and artifact.session_id == session_id:
                if artifact.status != ArtifactStatus.DELETED:
                    artifacts.append(artifact)

        return artifacts

    async def list_by_workflow_execution(
        self,
        workflow_execution_id: str,
    ) -> list[Artifact]:
        """获取工作流执行的产物列表
        
        Args:
            workflow_execution_id: 工作流执行 ID
        
        Returns:
            产物列表
        """
        artifacts = []

        for filename in os.listdir(self.metadata_path):
            if not filename.endswith(".json"):
                continue

            artifact_id = filename[:-5]
            artifact = self._load_artifact(artifact_id)

            if artifact and artifact.workflow_execution_id == workflow_execution_id:
                if artifact.status != ArtifactStatus.DELETED:
                    artifacts.append(artifact)

        return artifacts

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> list[Artifact]:
        """搜索产物
        
        Args:
            user_id: 用户 ID
            query: 搜索关键词
            limit: 最大数量
        
        Returns:
            匹配的产物列表
        """
        query_lower = query.lower()
        matched = []

        for filename in os.listdir(self.metadata_path):
            if not filename.endswith(".json"):
                continue

            artifact_id = filename[:-5]
            artifact = self._load_artifact(artifact_id)

            if not artifact or artifact.user_id != user_id:
                continue

            if artifact.status == ArtifactStatus.DELETED:
                continue

            # 匹配名称、描述、标签
            if (
                query_lower in artifact.name.lower()
                or query_lower in artifact.description.lower()
                or any(query_lower in tag.lower() for tag in artifact.tags)
            ):
                matched.append(artifact)

        matched.sort(key=lambda a: a.updated_at, reverse=True)

        return matched[:limit]


_global_manager: ArtifactManager | None = None


def get_artifact_manager() -> ArtifactManager:
    """获取全局产物管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ArtifactManager()
    return _global_manager


def reset_manager() -> None:
    """重置管理器（用于测试）"""
    global _global_manager
    _global_manager = ArtifactManager()
