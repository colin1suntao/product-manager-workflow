"""Redis消息队列"""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import redis.asyncio as aioredis

from pm_workstation.storage.redis_config import redis_config


class MessageQueue:
    """Redis消息队列"""

    def __init__(self, config: Any | None = None):
        """初始化消息队列

        Args:
            config: Redis配置
        """
        self.config = config or redis_config
        self._pool: aioredis.ConnectionPool | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listen_task: asyncio.Task | None = None
        self._client: aioredis.Redis | None = None

    async def connect(self):
        """连接Redis"""
        if self._pool is None:
            self._pool = self.config.create_pool()
            self._client = aioredis.Redis(connection_pool=self._pool)

    async def disconnect(self):
        """断开Redis连接"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            self._listen_task = None

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        if self._client:
            await self._client.aclose()
            self._client = None

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

        message_json = json.dumps(message)
        client = await self.get_client()
        return await client.publish(channel, message_json)

    async def subscribe(
        self,
        channels: list[str],
        callback: Callable | None = None,
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

        client = await self.get_client()
        self._pubsub = client.pubsub()

        await self._pubsub.subscribe(*channels)

        if callback:
            self._listen_task = asyncio.create_task(self._listen(callback))

        return self._pubsub

    async def unsubscribe(self, channels: list[str] | None = None):
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

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await callback(message["channel"], data)
                    except json.JSONDecodeError:
                        await callback(message["channel"], message["data"])
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Error in message listener")

    async def get_client(self) -> aioredis.Redis:
        """获取Redis客户端"""
        if self._pool is None:
            await self.connect()
        if self._client is None:
            self._client = aioredis.Redis(connection_pool=self._pool)
        return self._client

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
