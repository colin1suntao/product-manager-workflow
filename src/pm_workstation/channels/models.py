"""渠道模型定义"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChannelType(StrEnum):
    FEISHU = "feishu"
    WECHAT = "wechat"


class ChannelStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ChannelConfig(BaseModel):
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    name: str
    channel_type: ChannelType
    status: ChannelStatus = ChannelStatus.INACTIVE
    config: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_error: str | None = None
    webhook_url: str | None = None
    message_count: int = 0


class IncomingMessage(BaseModel):
    channel_id: str
    channel_type: ChannelType
    user_id: str
    user_name: str = ""
    content: str
    raw_event: dict[str, Any] = {}
    message_id: str = ""
    chat_id: str = ""


class OutgoingMessage(BaseModel):
    content: str
    message_id: str = ""
    chat_id: str = ""
    user_id: str = ""
