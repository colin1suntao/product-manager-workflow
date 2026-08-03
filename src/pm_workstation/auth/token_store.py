"""Token 撤销存储模块

使用 Redis 存储已撤销的 Refresh Token JTI，实现 Token 黑名单机制。
"""



class TokenStore:
    """Token 撤销存储"""

    def __init__(self) -> None:
        self._revoked_tokens: dict[str, int] = {}

    async def revoke_token(self, jti: str, expires_at: int) -> None:
        """撤销 Token

        Args:
            jti: Token 的唯一标识
            expires_at: Token 原始过期时间戳（用于自动清理）
        """
        self._revoked_tokens[jti] = expires_at

    async def is_revoked(self, jti: str) -> bool:
        """检查 Token 是否已被撤销

        Args:
            jti: Token 的唯一标识

        Returns:
            是否已撤销
        """
        return jti in self._revoked_tokens

    async def cleanup_expired(self) -> int:
        """清理已过期的撤销记录

        Returns:
            清理的记录数量
        """
        import time
        now = int(time.time())
        expired = [jti for jti, exp in self._revoked_tokens.items() if exp < now]
        for jti in expired:
            del self._revoked_tokens[jti]
        return len(expired)


# 全局单例
token_store = TokenStore()
