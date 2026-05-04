"""模型适配器测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.model_router.anthropic_adapter import AnthropicAdapter
from pm_workstation.model_router.base import LLMBackend, LLMConfig, LLMMessage, LLMResponse
from pm_workstation.model_router.openai_adapter import OpenAIAdapter


class TestLLMConfig:
    """LLMConfig测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig(model="gpt-4")
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.api_key == ""
        assert config.base_url is None
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = LLMConfig(
            model="claude-3-opus",
            temperature=0.5,
            max_tokens=2048,
            api_key="test-key",
            base_url="https://custom.api.com",
        )
        
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.api_key == "test-key"
        assert config.base_url == "https://custom.api.com"


class TestLLMMessage:
    """LLMMessage测试"""
    
    def test_create_message(self):
        """测试创建消息"""
        msg = LLMMessage(role="user", content="你好")
        
        assert msg.role == "user"
        assert msg.content == "你好"
    
    def test_system_message(self):
        """测试系统消息"""
        msg = LLMMessage(role="system", content="你是一个助手")
        
        assert msg.role == "system"


class TestLLMResponse:
    """LLMResponse测试"""
    
    def test_create_response(self):
        """测试创建响应"""
        response = LLMResponse(
            content="你好，我是助手",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
        )
        
        assert response.content == "你好，我是助手"
        assert response.model == "gpt-4"
        assert response.usage["total_tokens"] == 30
    
    def test_response_defaults(self):
        """测试响应默认值"""
        response = LLMResponse(
            content="测试",
            model="gpt-4",
        )
        
        assert response.usage is None
        assert response.finish_reason is None


class TestOpenAIAdapter:
    """OpenAI适配器测试"""
    
    def test_create_adapter(self):
        """测试创建适配器"""
        config = LLMConfig(
            model="gpt-4",
            api_key="test-key",
        )
        adapter = OpenAIAdapter(config)
        
        assert adapter.get_model_name() == "openai:gpt-4"
        assert adapter.is_available() is True
    
    def test_adapter_not_available_without_key(self):
        """测试没有API密钥时不可用"""
        config = LLMConfig(model="gpt-4")
        adapter = OpenAIAdapter(config)
        
        assert adapter.is_available() is False
    
    def test_custom_base_url(self):
        """测试自定义base_url"""
        config = LLMConfig(
            model="gpt-4",
            api_key="test-key",
            base_url="https://custom.api.com",
        )
        adapter = OpenAIAdapter(config)
        
        assert adapter.config.base_url == "https://custom.api.com"
    
    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """测试聊天完成"""
        config = LLMConfig(model="gpt-4", api_key="test-key")
        adapter = OpenAIAdapter(config)
        
        # Mock OpenAI客户端
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="你好"),
                finish_reason="stop",
            )
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            response = await adapter.chat(
                messages=[LLMMessage(role="user", content="你好")]
            )
            
            assert response.content == "你好"
            assert response.model == "gpt-4"
            assert response.usage["total_tokens"] == 30
    
    @pytest.mark.asyncio
    async def test_chat_stream(self):
        """测试流式聊天"""
        config = LLMConfig(model="gpt-4", api_key="test-key")
        adapter = OpenAIAdapter(config)
        
        # Mock流式响应
        async def mock_stream():
            chunks = [
                MagicMock(choices=[MagicMock(delta=MagicMock(content="你"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content="好"))]),
            ]
            for chunk in chunks:
                yield chunk
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            chunks = []
            async for chunk in adapter.chat_stream(
                messages=[LLMMessage(role="user", content="你好")]
            ):
                chunks.append(chunk)
            
            assert chunks == ["你", "好"]


class TestAnthropicAdapter:
    """Anthropic适配器测试"""
    
    def test_create_adapter(self):
        """测试创建适配器"""
        config = LLMConfig(
            model="claude-3-opus",
            api_key="test-key",
        )
        adapter = AnthropicAdapter(config)
        
        assert adapter.get_model_name() == "anthropic:claude-3-opus"
        assert adapter.is_available() is True
    
    def test_adapter_not_available_without_key(self):
        """测试没有API密钥时不可用"""
        config = LLMConfig(model="claude-3-opus")
        adapter = AnthropicAdapter(config)
        
        assert adapter.is_available() is False
    
    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """测试聊天完成"""
        config = LLMConfig(model="claude-3-opus", api_key="test-key")
        adapter = AnthropicAdapter(config)
        
        # Mock Anthropic客户端
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="你好")]
        mock_response.usage = MagicMock(
            input_tokens=10,
            output_tokens=20,
        )
        mock_response.stop_reason = "end_turn"
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            response = await adapter.chat(
                messages=[
                    LLMMessage(role="system", content="你是一个助手"),
                    LLMMessage(role="user", content="你好"),
                ]
            )
            
            assert response.content == "你好"
            assert response.model == "claude-3-opus"
            assert response.usage["total_tokens"] == 30
            assert response.finish_reason == "end_turn"
    
    @pytest.mark.asyncio
    async def test_chat_with_system_message(self):
        """测试带系统消息的聊天"""
        config = LLMConfig(model="claude-3-opus", api_key="test-key")
        adapter = AnthropicAdapter(config)
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="回答")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"
        
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            await adapter.chat(
                messages=[
                    LLMMessage(role="system", content="系统提示"),
                    LLMMessage(role="user", content="问题"),
                ]
            )
            
            # 验证调用参数
            call_args = mock_client.messages.create.call_args
            assert call_args.kwargs["system"] == "系统提示"
            assert len(call_args.kwargs["messages"]) == 1
    
    @pytest.mark.asyncio
    async def test_chat_stream(self):
        """测试流式聊天"""
        config = LLMConfig(model="claude-3-opus", api_key="test-key")
        adapter = AnthropicAdapter(config)
        
        # Mock流式响应
        class MockStream:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
            
            @property
            async def text_stream(self):
                for text in ["你", "好"]:
                    yield text
        
        mock_client = AsyncMock()
        mock_client.messages.stream = MagicMock(return_value=MockStream())
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            chunks = []
            async for chunk in adapter.chat_stream(
                messages=[LLMMessage(role="user", content="你好")]
            ):
                chunks.append(chunk)
            
            assert chunks == ["你", "好"]


class TestAdapterIntegration:
    """适配器集成测试"""
    
    def test_openai_config_with_base_url(self):
        """测试OpenAI配置base_url"""
        config = LLMConfig(
            model="gpt-4",
            api_key="test-key",
            base_url="https://api.openai-proxy.com/v1",
        )
        adapter = OpenAIAdapter(config)
        
        # 验证客户端创建时使用base_url
        with patch("openai.AsyncOpenAI") as mock_openai:
            adapter._get_client()
            mock_openai.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.openai-proxy.com/v1",
            )
    
    def test_anthropic_config_with_base_url(self):
        """测试Anthropic配置base_url"""
        config = LLMConfig(
            model="claude-3-opus",
            api_key="test-key",
            base_url="https://api.anthropic-proxy.com",
        )
        adapter = AnthropicAdapter(config)
        
        # 验证客户端创建时使用base_url
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            adapter._get_client()
            mock_anthropic.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.anthropic-proxy.com",
            )
    
    @pytest.mark.asyncio
    async def test_multiple_chat_calls(self):
        """测试多次聊天调用"""
        config = LLMConfig(model="gpt-4", api_key="test-key")
        adapter = OpenAIAdapter(config)
        
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="回答"), finish_reason="stop")
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        with patch.object(adapter, '_get_client', return_value=mock_client):
            # 第一次调用
            response1 = await adapter.chat(
                messages=[LLMMessage(role="user", content="问题1")]
            )
            
            # 第二次调用
            response2 = await adapter.chat(
                messages=[LLMMessage(role="user", content="问题2")]
            )
            
            assert response1.content == "回答"
            assert response2.content == "回答"
            assert mock_client.chat.completions.create.call_count == 2
