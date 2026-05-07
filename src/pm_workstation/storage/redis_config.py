"""Redis消息队列配置"""


import redis.asyncio as aioredis

from pm_workstation.config import settings


class RedisConfig:
    """Redis配置"""

    def __init__(
        self,
        url: str | None = None,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
    ):
        self.url = url or settings.redis_url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout

    def create_pool(self) -> aioredis.ConnectionPool:
        """创建连接池"""
        return aioredis.ConnectionPool.from_url(
            self.url,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            decode_responses=True,
        )


# 全局Redis配置
redis_config = RedisConfig()
