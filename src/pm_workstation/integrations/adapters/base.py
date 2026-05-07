"""集成适配器抽象基类

定义所有外部系统适配器的统一接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from pm_workstation.integrations.models import IntegrationConfig, SyncTask


class SyncDataType(StrEnum):
    """同步数据类型"""
    REQUIREMENT = "requirement"
    TASK = "task"
    PROTOTYPE = "prototype"
    DOCUMENT = "document"
    COMPONENT = "component"
    USER_STORY = "user_story"
    EPIC = "epic"


@dataclass
class SyncItem:
    """单条同步数据项"""
    external_id: str
    data_type: SyncDataType
    title: str
    description: str
    status: str = ""
    url: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """同步任务结果"""
    success: bool
    items: list[SyncItem] = field(default_factory=list)
    total_count: int = 0
    synced_count: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class BaseIntegrationAdapter(ABC):
    """集成适配器抽象基类

    所有外部系统适配器必须继承此类并实现抽象方法。
    """

    def __init__(self, config: IntegrationConfig):
        """初始化适配器

        Args:
            config: 集成配置，包含连接信息和凭据
        """
        self.config = config
        self._client: Any = None

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称（人类可读）"""
        ...

    @abstractmethod
    def authenticate(self) -> bool:
        """验证连接凭据

        Returns:
            认证成功返回 True
        """
        ...

    @abstractmethod
    def import_data(
        self,
        task: SyncTask,
        data_types: list[SyncDataType] | None = None,
    ) -> SyncResult:
        """从外部系统导入数据

        Args:
            task: 同步任务
            data_types: 要导入的数据类型，None 表示全部

        Returns:
            同步结果
        """
        ...

    @abstractmethod
    def export_data(
        self,
        task: SyncTask,
        data_types: list[SyncDataType] | None = None,
    ) -> SyncResult:
        """向外部系统导出数据

        Args:
            task: 同步任务
            data_types: 要导出的数据类型，None 表示全部

        Returns:
            同步结果
        """
        ...

    @abstractmethod
    def get_remote_status(self, task: SyncTask) -> SyncResult:
        """获取远程同步任务状态

        Args:
            task: 同步任务

        Returns:
            同步结果（包含远程状态信息）
        """
        ...

    def validate_config(self) -> list[str]:
        """验证配置完整性

        Returns:
            错误信息列表，空列表表示配置有效
        """
        errors: list[str] = []
        if not self.config.name:
            errors.append("配置名称不能为空")
        if not self.config.api_endpoint and not self.config.api_key:
            errors.append("需要配置 API 地址或 API 密钥")
        return errors

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """构建请求头

        Args:
            extra: 额外的请求头

        Returns:
            完整的请求头字典
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if extra:
            headers.update(extra)

        return headers

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} endpoint={self.config.api_endpoint}>"
