"""LLM Provider 配置模型"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LLMProviderType(str, Enum):
    """LLM 提供商类型"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class LLMProviderConfig(BaseModel):
    """LLM Provider 配置"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=100, description="显示名称")
    provider_type: LLMProviderType = Field(description="提供商类型")
    api_key: str = Field(min_length=1, description="API Key")
    base_url: Optional[str] = Field(default=None, max_length=500, description="API Base URL")
    default_model: str = Field(min_length=1, max_length=100, description="默认模型名称")
    is_active: bool = Field(default=True, description="是否启用")
    is_default: bool = Field(default=False, description="是否为默认 Provider")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_display_dict(self) -> dict:
        """返回用于显示的字典（隐藏 API Key）"""
        return {
            "id": self.id,
            "name": self.name,
            "provider_type": self.provider_type.value,
            "api_key": self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***",
            "base_url": self.base_url,
            "default_model": self.default_model,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
