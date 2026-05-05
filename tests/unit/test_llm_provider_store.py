"""LLM Provider 存储测试"""

import pytest

from pm_workstation.llm.models import LLMProviderConfig, LLMProviderType
from pm_workstation.llm.provider_store import LLMProviderStore


@pytest.fixture
def store():
    return LLMProviderStore()


@pytest.fixture
def openai_config():
    return LLMProviderConfig(
        name="OpenAI",
        provider_type=LLMProviderType.OPENAI,
        api_key="sk-test-openai-key-12345",
        default_model="gpt-4o",
    )


@pytest.fixture
def custom_config():
    return LLMProviderConfig(
        name="DeepSeek",
        provider_type=LLMProviderType.CUSTOM,
        api_key="sk-test-deepseek-key",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
    )


@pytest.mark.asyncio
async def test_create_config(store, openai_config):
    config = await store.create_config(openai_config)
    assert config.id is not None
    assert config.name == "OpenAI"
    assert config.provider_type == LLMProviderType.OPENAI


@pytest.mark.asyncio
async def test_get_config(store, openai_config):
    created = await store.create_config(openai_config)
    fetched = await store.get_config(created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_configs(store, openai_config, custom_config):
    await store.create_config(openai_config)
    await store.create_config(custom_config)
    configs = await store.list_configs()
    assert len(configs) == 2


@pytest.mark.asyncio
async def test_update_config(store, openai_config):
    created = await store.create_config(openai_config)
    updated = await store.update_config(created.id, {"name": "OpenAI Updated"})
    assert updated is not None
    assert updated.name == "OpenAI Updated"


@pytest.mark.asyncio
async def test_update_nonexistent_config(store):
    updated = await store.update_config("nonexistent-id", {"name": "Test"})
    assert updated is None


@pytest.mark.asyncio
async def test_delete_config(store, openai_config):
    created = await store.create_config(openai_config)
    deleted = await store.delete_config(created.id)
    assert deleted is True
    assert await store.get_config(created.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_config(store):
    deleted = await store.delete_config("nonexistent-id")
    assert deleted is False


@pytest.mark.asyncio
async def test_set_default_config(store, openai_config, custom_config):
    config1 = await store.create_config(openai_config)
    config2 = await store.create_config(custom_config)

    await store.set_default(config2.id)
    default = await store.get_default_config()
    assert default is not None
    assert default.id == config2.id


@pytest.mark.asyncio
async def test_default_config_uniqueness(store, openai_config, custom_config):
    config1 = await store.create_config(openai_config)
    config2 = await store.create_config(custom_config)

    await store.set_default(config1.id)
    await store.set_default(config2.id)

    configs = await store.list_configs()
    default_count = sum(1 for c in configs if c.is_default)
    assert default_count == 1


@pytest.mark.asyncio
async def test_get_default_returns_first_active(store, openai_config):
    config = await store.create_config(openai_config)
    default = await store.get_default_config()
    assert default is not None
    assert default.id == config.id


@pytest.mark.asyncio
async def test_display_dict_masks_api_key(store, openai_config):
    created = await store.create_config(openai_config)
    display = created.to_display_dict()
    assert "sk-test-..." in display["api_key"] or "***" in display["api_key"]
    assert openai_config.api_key not in display["api_key"]
