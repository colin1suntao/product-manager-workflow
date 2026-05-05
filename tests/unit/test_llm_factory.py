"""LLM 工厂测试"""

import pytest

from pm_workstation.llm.factory import LLMFactory
from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType
from pm_workstation.model_router.base import LLMBackend


class TestLLMFactory:
    def test_create_openai_adapter(self):
        config = LLMProviderConfig(
            name="OpenAI",
            provider_type=LLMProviderType.OPENAI,
            api_key="sk-test-key",
            default_model="gpt-4o",
        )
        adapter = LLMFactory.create_adapter(config)
        assert isinstance(adapter, LLMBackend)

    def test_create_anthropic_adapter(self):
        config = LLMProviderConfig(
            name="Anthropic",
            provider_type=LLMProviderType.ANTHROPIC,
            api_key="sk-ant-test-key",
            default_model="claude-3-5-sonnet-20241022",
        )
        adapter = LLMFactory.create_adapter(config)
        assert isinstance(adapter, LLMBackend)

    def test_create_custom_adapter(self):
        config = LLMProviderConfig(
            name="DeepSeek",
            provider_type=LLMProviderType.CUSTOM,
            api_key="sk-deepseek-key",
            base_url="https://api.deepseek.com/v1",
            default_model="deepseek-chat",
        )
        adapter = LLMFactory.create_adapter(config)
        assert isinstance(adapter, LLMBackend)

    def test_custom_adapter_requires_base_url(self):
        config = LLMProviderConfig(
            name="Custom",
            provider_type=LLMProviderType.CUSTOM,
            api_key="sk-custom-key",
            default_model="custom-model",
        )
        with pytest.raises(ValueError, match="base_url"):
            LLMFactory.create_adapter(config)

    def test_invalid_provider_type(self):
        config = LLMProviderConfig(
            name="Invalid",
            provider_type=LLMProviderType.OPENAI,  # Use valid type but modify after
            api_key="sk-test",
            default_model="test",
        )
        # Force invalid type for testing
        config.provider_type = "invalid"  # type: ignore
        with pytest.raises(ValueError):
            LLMFactory.create_adapter(config)
