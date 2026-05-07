"""组件存储接口"""

from abc import ABC, abstractmethod

from pm_workstation.models.component import (
    Component,
    ComponentSearchRequest,
    ComponentSearchResult,
    ComponentVersion,
)


class ComponentStore(ABC):
    """组件存储抽象基类

    提供组件的CRUD操作、搜索和版本管理。
    """

    @abstractmethod
    async def create_component(self, component: Component) -> Component:
        """创建新组件

        Args:
            component: 组件定义

        Returns:
            创建的组件（含生成的ID）
        """
        pass

    @abstractmethod
    async def get_component(self, component_id: str) -> Component | None:
        """获取组件

        Args:
            component_id: 组件ID

        Returns:
            组件定义，不存在时返回None
        """
        pass

    @abstractmethod
    async def update_component(self, component_id: str, **kwargs) -> Component | None:
        """更新组件

        Args:
            component_id: 组件ID
            **kwargs: 要更新的字段

        Returns:
            更新后的组件，不存在时返回None
        """
        pass

    @abstractmethod
    async def delete_component(self, component_id: str) -> bool:
        """删除组件及其所有版本

        Args:
            component_id: 组件ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def list_components(
        self,
        category: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Component]:
        """列出组件

        Args:
            category: 分类过滤
            status: 状态过滤
            tags: 标签过滤（包含所有指定标签）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            组件列表
        """
        pass

    @abstractmethod
    async def create_version(self, version: ComponentVersion) -> ComponentVersion:
        """创建组件版本

        Args:
            version: 版本定义

        Returns:
            创建的版本
        """
        pass

    @abstractmethod
    async def get_version(
        self,
        component_id: str,
        version: str,
    ) -> ComponentVersion | None:
        """获取指定版本

        Args:
            component_id: 组件ID
            version: 版本号

        Returns:
            版本信息，不存在时返回None
        """
        pass

    @abstractmethod
    async def get_latest_version(self, component_id: str) -> ComponentVersion | None:
        """获取最新版本

        Args:
            component_id: 组件ID

        Returns:
            最新版本，不存在时返回None
        """
        pass

    @abstractmethod
    async def list_versions(
        self,
        component_id: str,
        limit: int = 20,
    ) -> list[ComponentVersion]:
        """列出组件所有版本

        Args:
            component_id: 组件ID
            limit: 返回数量限制

        Returns:
            版本列表（按创建时间倒序）
        """
        pass

    @abstractmethod
    async def search(self, request: ComponentSearchRequest) -> list[ComponentSearchResult]:
        """搜索组件

        Args:
            request: 搜索请求

        Returns:
            搜索结果列表（按相似度排序）
        """
        pass

    @abstractmethod
    async def match_component(
        self,
        description: str,
        category_hint: str | None = None,
        min_similarity: float = 0.6,
    ) -> ComponentSearchResult | None:
        """匹配最合适的组件（用于原型生成）

        Args:
            description: 组件功能描述
            category_hint: 分类提示
            min_similarity: 最低相似度

        Returns:
            最佳匹配结果，无匹配时返回None
        """
        pass
