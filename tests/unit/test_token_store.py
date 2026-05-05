"""TokenStore 测试"""

import asyncio
import time

import pytest

from pm_workstation.auth.token_store import TokenStore


class TestTokenStore:
    @pytest.fixture
    def store(self):
        return TokenStore()

    @pytest.mark.asyncio
    async def test_revoke_and_check(self, store):
        jti = "test-jti-123"
        expires_at = int(time.time()) + 3600
        await store.revoke_token(jti, expires_at)
        assert await store.is_revoked(jti) is True

    @pytest.mark.asyncio
    async def test_non_revoked_token(self, store):
        assert await store.is_revoked("non-existent-jti") is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, store):
        now = int(time.time())
        await store.revoke_token("expired-jti", now - 100)
        await store.revoke_token("valid-jti", now + 3600)

        cleaned = await store.cleanup_expired()
        assert cleaned == 1
        assert await store.is_revoked("expired-jti") is False
        assert await store.is_revoked("valid-jti") is True

    @pytest.mark.asyncio
    async def test_multiple_revokes(self, store):
        await store.revoke_token("jti-1", int(time.time()) + 3600)
        await store.revoke_token("jti-2", int(time.time()) + 3600)
        await store.revoke_token("jti-3", int(time.time()) + 3600)

        assert await store.is_revoked("jti-1") is True
        assert await store.is_revoked("jti-2") is True
        assert await store.is_revoked("jti-3") is True
        assert await store.is_revoked("jti-4") is False

    @pytest.mark.asyncio
    async def test_revoke_same_jti(self, store):
        jti = "duplicate-jti"
        await store.revoke_token(jti, int(time.time()) + 3600)
        await store.revoke_token(jti, int(time.time()) + 7200)
        assert await store.is_revoked(jti) is True
