"""LLM Provider 配置存储

提供 LLM Provider 配置的持久化操作。
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType


PERSISTENCE_FILE = os.path.join(os.path.dirname(__file__), ".provider_cache.json")


class LLMProviderStore:
    """LLM Provider 配置存储"""

    def __init__(self):
        self._configs: Dict[str, LLMProviderConfig] = {}
        self._load_from_file()

    def _persistence_path(self) -> str:
        return PERSISTENCE_FILE

    def _load_from_file(self) -> None:
        path = self._persistence_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for item in data:
                config = LLMProviderConfig(**item)
                self._configs[config.id] = config
        except Exception:
            pass

    def _save_to_file(self) -> None:
        path = self._persistence_path()
        try:
            data = [c.model_dump(mode="json") for c in self._configs.values()]
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    async def create_config(self, config: LLMProviderConfig) -> LLMProviderConfig:
        """创建新的 LLM Provider 配置

        Args:
            config: LLM Provider 配置对象

        Returns:
            创建的配置对象
        """
        # 如果设置为默认，取消其他默认
        if config.is_default:
            for c in self._configs.values():
                c.is_default = False

        config.updated_at = datetime.now(timezone.utc)
        self._configs[config.id] = config
        self._save_to_file()
        return config

    async def get_config(self, config_id: str) -> Optional[LLMProviderConfig]:
        """通过 ID 获取配置

        Args:
            config_id: 配置唯一标识

        Returns:
            配置对象，未找到时返回 None
        """
        return self._configs.get(config_id)

    async def list_configs(self) -> List[LLMProviderConfig]:
        """列出所有配置

        Returns:
            所有配置列表
        """
        return list(self._configs.values())

    async def update_config(self, config_id: str, updates: dict) -> Optional[LLMProviderConfig]:
        """更新配置

        Args:
            config_id: 配置唯一标识
            updates: 要更新的字段字典

        Returns:
            更新后的配置对象，未找到时返回 None
        """
        config = self._configs.get(config_id)
        if not config:
            return None

        # 如果设置为默认，取消其他默认
        if updates.get("is_default", False):
            for c in self._configs.values():
                if c.id != config_id:
                    c.is_default = False

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.now(timezone.utc)
        self._save_to_file()
        return config

    async def delete_config(self, config_id: str) -> bool:
        """删除配置

        Args:
            config_id: 配置唯一标识

        Returns:
            是否删除成功
        """
        if config_id in self._configs:
            del self._configs[config_id]
            self._save_to_file()
            return True
        return False

    async def get_default_config(self) -> Optional[LLMProviderConfig]:
        """获取默认配置

        Returns:
            默认配置对象，未找到时返回 None
        """
        for config in self._configs.values():
            if config.is_default and config.is_active:
                return config
        # 如果没有默认，返回第一个启用的配置
        for config in self._configs.values():
            if config.is_active:
                return config
        return None

    async def set_default(self, config_id: str) -> bool:
        """设置默认配置

        Args:
            config_id: 配置唯一标识

        Returns:
            是否设置成功
        """
        config = self._configs.get(config_id)
        if not config:
            return False

        for c in self._configs.values():
            c.is_default = c.id == config_id

        config.updated_at = datetime.now(timezone.utc)
        self._save_to_file()
        return True


# 全局单例
_provider_store = LLMProviderStore()
