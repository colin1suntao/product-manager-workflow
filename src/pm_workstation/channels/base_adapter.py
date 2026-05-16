"""渠道适配器基类"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from pm_workstation.channels.models import ChannelConfig, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class ChannelAdapter(ABC):
    def __init__(self, config: ChannelConfig):
        self.config = config

    @abstractmethod
    async def validate_webhook(self, request_data: dict[str, Any], headers: dict[str, str] = {}) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def parse_incoming(self, request_data: dict[str, Any], headers: dict[str, str] = {}) -> IncomingMessage | None:
        pass

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        pass

    @abstractmethod
    def get_webhook_url_hint(self) -> str:
        pass

    def validate_config(self) -> tuple[bool, str]:
        return True, ""
