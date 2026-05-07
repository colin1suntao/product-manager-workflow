"""MinIO/S3存储后端"""

import io
from datetime import timedelta
from typing import BinaryIO

from pm_workstation.config import settings
from pm_workstation.storage.base import StorageBackend, StorageObject


class MinIOStorage(StorageBackend):
    """MinIO/S3对象存储"""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool = False,
    ):
        from minio import Minio

        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.bucket = bucket or settings.minio_bucket

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure,
        )

        # 确保bucket存在
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def upload(
        self,
        key: str,
        data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> StorageObject:
        """上传文件到MinIO"""
        content = data.read()
        data_stream = io.BytesIO(content)

        self.client.put_object(
            self.bucket,
            key,
            data_stream,
            length=len(content),
            content_type=content_type,
        )

        return StorageObject(
            key=key,
            size=len(content),
            content_type=content_type,
        )

    async def download(self, key: str) -> BinaryIO:
        """从MinIO下载文件"""
        response = self.client.get_object(self.bucket, key)
        content = response.read()
        response.close()
        response.release_conn()

        return io.BytesIO(content)

    async def delete(self, key: str) -> bool:
        """删除MinIO文件"""
        try:
            self.client.remove_object(self.bucket, key)
            return True
        except Exception:
            return False

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """获取预签名URL"""
        return self.client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(seconds=expires_in),
        )

    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except Exception:
            return False
