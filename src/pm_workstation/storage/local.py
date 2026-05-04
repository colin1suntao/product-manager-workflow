"""本地存储后端"""

import shutil
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

from pm_workstation.config import settings
from pm_workstation.storage.base import StorageBackend, StorageObject


class LocalStorage(StorageBackend):
    """本地文件系统存储"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """获取文件路径"""
        return self.base_path / key
    
    async def upload(
        self,
        key: str,
        data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> StorageObject:
        """上传文件到本地"""
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取数据并写入文件
        content = data.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return StorageObject(
            key=key,
            size=len(content),
            content_type=content_type,
            url=f"file://{file_path}",
        )
    
    async def download(self, key: str) -> BinaryIO:
        """从本地下载文件"""
        file_path = self._get_file_path(key)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        return BytesIO(file_path.read_bytes())
    
    async def delete(self, key: str) -> bool:
        """删除本地文件"""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """获取本地文件URL"""
        file_path = self._get_file_path(key)
        return f"file://{file_path}"
    
    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        return self._get_file_path(key).exists()
