"""Redis消息队列"""

import json
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

from pm_workstation.storage.redis_config import redis_config


class MessageQueue:
    """Redis消息队列"""
    
    def __init__(self, config: Optional[Any] = None):
        """初始化消息队列
        
        Args:
            config: Redis配置
        """
        self.config = config or redis_config
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
    
    async def connect(self):
        """连接到Redis"""
        if self._pool is None:
            self._pool = self.config.create_pool()
    
    async def disconnect(self):
        """断开Redis连接"""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None
        
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
    
    async def publish(self, channel: str, message: dict) -> int:
        """发布消息
        
        Args:
            channel: 频道名称
            message: 消息内容（字典）
            
        Returns:
            订阅者数量
        """
        if self._pool is None:
            await self.connect()
        
        redis_client = aioredis.Redis(connection_pool=self._pool)
        
        message_json = json.dumps(message)
        return await redis_client.publish(channel, message_json)
    
    async def subscribe(
        self,
        channels: list[str],
        callback: Optional[Callable] = None,
    ) -> aioredis.client.PubSub:
        """订阅频道
        
        Args:
            channels: 频道列表
            callback: 消息回调函数
            
        Returns:
            PubSub对象
        """
        if self._pool is None:
            await self.connect()
        
        redis_client = aioredis.Redis(connection_pool=self._pool)
        self._pubsub = redis_client.pubsub()
        
        await self._pubsub.subscribe(*channels)
        
        if callback:
            # 在后台处理消息
            import asyncio
            asyncio.create_task(self._listen(callback))
        
        return self._pubsub
    
    async def unsubscribe(self, channels: Optional[list[str]] = None):
        """取消订阅
        
        Args:
            channels: 频道列表，None时取消所有订阅
        """
        if self._pubsub:
            if channels:
                await self._pubsub.unsubscribe(*channels)
            else:
                await self._pubsub.unsubscribe()
    
    async def _listen(self, callback: Callable):
        """监听消息
        
        Args:
            callback: 消息回调函数
        """
        if not self._pubsub:
            return
        
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await callback(message["channel"], data)
                except json.JSONDecodeError:
                    # 非JSON消息，直接传递原始数据
                    await callback(message["channel"], message["data"])
    
    async def get_client(self) -> aioredis.Redis:
        """获取Redis客户端"""
        if self._pool is None:
            await self.connect()
        
        return aioredis.Redis(connection_pool=self._pool)
    
    async def health_check(self) -> bool:
        """健康检查
        
        Returns:
            是否健康
        """
        try:
            if self._pool is None:
                await self.connect()
            
            client = await self.get_client()
            return await client.ping()
        except Exception:
            return False


# 全局消息队列实例
message_queue = MessageQueue()
