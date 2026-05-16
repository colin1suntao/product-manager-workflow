"""渠道配置存储"""

import logging
from typing import Optional

from pm_workstation.channels.models import ChannelConfig, ChannelStatus, ChannelType

logger = logging.getLogger(__name__)


class ChannelStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configs: dict[str, ChannelConfig] = {}
        return cls._instance

    async def create(self, config: ChannelConfig) -> ChannelConfig:
        self._configs[config.id] = config
        logger.info(f"[ChannelStore] Created channel: {config.id} ({config.channel_type.value})")
        return config

    async def get(self, channel_id: str) -> Optional[ChannelConfig]:
        return self._configs.get(channel_id)

    async def list_all(self) -> list[ChannelConfig]:
        return list(self._configs.values())

    async def update(self, channel_id: str, updates: dict) -> Optional[ChannelConfig]:
        config = self._configs.get(channel_id)
        if not config:
            return None
        for k, v in updates.items():
            if hasattr(config, k):
                setattr(config, k, v)
        from datetime import datetime
        config.updated_at = datetime.now()
        self._configs[channel_id] = config
        return config

    async def delete(self, channel_id: str) -> bool:
        if channel_id in self._configs:
            del self._configs[channel_id]
            return True
        return False

    async def increment_message_count(self, channel_id: str) -> None:
        config = self._configs.get(channel_id)
        if config:
            config.message_count += 1
