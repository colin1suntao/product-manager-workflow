"""存储层接口"""

from abc import ABC, abstractmethod
from typing import BinaryIO

from pydantic import BaseModel


class StorageObject(BaseModel):
    """存储对象元数据"""
    key: str
    size: int
    content_type: str
    url: str | None = None


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> StorageObject:
        """上传文件

        Args:
            key: 存储键
            data: 文件数据流
            content_type: 内容类型

        Returns:
            存储对象元数据
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> BinaryIO:
        """下载文件

        Args:
            key: 存储键

        Returns:
            文件数据流
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除文件

        Args:
            key: 存储键

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """获取访问URL

        Args:
            key: 存储键
            expires_in: 过期时间（秒）

        Returns:
            访问URL
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在

        Args:
            key: 存储键

        Returns:
            是否存在
        """
        pass
