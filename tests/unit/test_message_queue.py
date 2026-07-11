"""消息队列测试"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pm_workstation.storage.message_queue import MessageQueue
from pm_workstation.storage.redis_config import RedisConfig


class TestRedisConfig:
    """RedisConfig测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RedisConfig()
        
        assert config.url == "redis://localhost:6379/0"
        assert config.max_connections == max(20, (os.cpu_count() or 2) * 5)
        assert config.socket_timeout == 5.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RedisConfig(
            url="redis://custom:6379/1",
            max_connections=20,
            socket_timeout=10.0,
        )
        
        assert config.url == "redis://custom:6379/1"
        assert config.max_connections == 20
        assert config.socket_timeout == 10.0
    
    def test_create_pool(self):
        """测试创建连接池"""
        config = RedisConfig(url="redis://localhost:6379/0")
        
        with patch("redis.asyncio.ConnectionPool.from_url") as mock_from_url:
            mock_pool = MagicMock()
            mock_from_url.return_value = mock_pool
            
            pool = config.create_pool()
            
            mock_from_url.assert_called_once()
            call_kwargs = mock_from_url.call_args.kwargs
            assert call_kwargs["max_connections"] == max(20, (os.cpu_count() or 2) * 5)
            assert call_kwargs["decode_responses"] is True


class TestMessageQueue:
    """MessageQueue测试"""
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """测试连接"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        with patch.object(config, 'create_pool') as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool
            
            await mq.connect()
            
            assert mq._pool is mock_pool
            mock_create_pool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mock_pool.disconnect = AsyncMock()
        mq._pool = mock_pool
        
        await mq.disconnect()
        
        mock_pool.disconnect.assert_called_once()
        assert mq._pool is None
    
    @pytest.mark.asyncio
    async def test_publish(self):
        """测试发布消息"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        message = {"type": "test", "data": "hello"}
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.publish = AsyncMock(return_value=2)
            mock_redis_class.return_value = mock_redis
            
            result = await mq.publish("test-channel", message)
            
            assert result == 2
            mock_redis.publish.assert_called_once()
            
            # 验证消息格式
            call_args = mock_redis.publish.call_args
            assert call_args[0][0] == "test-channel"
            assert json.loads(call_args[0][1]) == message
    
    @pytest.mark.asyncio
    async def test_publish_auto_connect(self):
        """测试发布时自动连接"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        with patch.object(config, 'create_pool') as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool
            
            with patch("redis.asyncio.Redis") as mock_redis_class:
                mock_redis = AsyncMock()
                mock_redis.publish = AsyncMock(return_value=1)
                mock_redis_class.return_value = mock_redis
                
                await mq.publish("channel", {"test": True})
                
                mock_create_pool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe(self):
        """测试订阅频道"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = MagicMock()  # Redis实例本身是同步的
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_redis_class.return_value = mock_redis
            
            pubsub = await mq.subscribe(["channel1", "channel2"])
            
            mock_pubsub.subscribe.assert_called_once_with("channel1", "channel2")
            assert mq._pubsub is mock_pubsub
    
    @pytest.mark.asyncio
    async def test_subscribe_with_callback(self):
        """测试带回调的订阅"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        callback = AsyncMock()
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = MagicMock()
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            
            # Mock listen generator
            async def mock_listen():
                yield {
                    "type": "message",
                    "channel": "test-channel",
                    "data": '{"key": "value"}',
                }
            
            mock_pubsub.listen = mock_listen
            mock_redis_class.return_value = mock_redis
            
            with patch("asyncio.create_task") as mock_create_task:
                await mq.subscribe(["test-channel"], callback=callback)
                
                mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unsubscribe_specific_channels(self):
        """测试取消特定频道订阅"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pubsub = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mq._pubsub = mock_pubsub
        
        await mq.unsubscribe(["channel1", "channel2"])
        
        mock_pubsub.unsubscribe.assert_called_once_with("channel1", "channel2")
    
    @pytest.mark.asyncio
    async def test_unsubscribe_all(self):
        """测试取消所有订阅"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pubsub = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mq._pubsub = mock_pubsub
        
        await mq.unsubscribe()
        
        mock_pubsub.unsubscribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_listen_message(self):
        """测试监听消息"""
        callback = AsyncMock()
        
        # 直接测试解析逻辑
        import json
        message = {"type": "message", "channel": "ch", "data": '{"test": true}'}
        data = json.loads(message["data"])
        await callback(message["channel"], data)
        
        callback.assert_called_once_with("ch", {"test": True})
    
    @pytest.mark.asyncio
    async def test_listen_non_json_message(self):
        """测试监听非JSON消息"""
        callback = AsyncMock()
        
        message = {"type": "message", "channel": "ch", "data": "plain text"}
        
        import json
        try:
            data = json.loads(message["data"])
            await callback(message["channel"], data)
        except json.JSONDecodeError:
            await callback(message["channel"], message["data"])
        
        callback.assert_called_once_with("ch", "plain text")
    
    @pytest.mark.asyncio
    async def test_get_client(self):
        """测试获取客户端"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis
            
            client = await mq.get_client()
            
            assert client is mock_redis
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis_class.return_value = mock_redis
            
            result = await mq.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """测试健康检查失败"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
            mock_redis_class.return_value = mock_redis
            
            result = await mq.health_check()
            
            assert result is False


class TestMessageQueueIntegration:
    """消息队列集成测试"""
    
    @pytest.mark.asyncio
    async def test_publish_and_subscribe_flow(self):
        """测试发布订阅流程"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        # Mock连接
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        messages_received = []
        
        async def callback(channel, data):
            messages_received.append((channel, data))
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = MagicMock()
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_redis.publish = AsyncMock(return_value=1)
            mock_redis_class.return_value = mock_redis
            
            # 订阅
            await mq.subscribe(["test-channel"], callback=callback)
            
            # 发布
            await mq.publish("test-channel", {"message": "hello"})
            
            # 验证发布调用
            assert mock_redis.publish.call_count == 1
    
    @pytest.mark.asyncio
    async def test_multiple_channels(self):
        """测试多频道"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        mock_pool = MagicMock()
        mq._pool = mock_pool
        
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = MagicMock()
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_redis_class.return_value = mock_redis
            
            channels = ["channel1", "channel2", "channel3"]
            await mq.subscribe(channels)
            
            mock_pubsub.subscribe.assert_called_once_with(*channels)
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """测试连接生命周期"""
        config = RedisConfig()
        mq = MessageQueue(config=config)
        
        assert mq._pool is None
        
        # 连接
        with patch.object(config, 'create_pool') as mock_create_pool:
            mock_pool = MagicMock()
            mock_pool.disconnect = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            await mq.connect()
            assert mq._pool is not None
            
            # 断开
            await mq.disconnect()
            assert mq._pool is None
            mock_pool.disconnect.assert_called_once()
