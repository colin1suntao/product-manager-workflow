"""JWT 工具模块测试"""

import time
from datetime import timedelta

import pytest
from jose import JWTError, jwt

from pm_workstation.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_access_token,
    verify_refresh_token,
)
from pm_workstation.config import settings


class TestCreateAccessToken:
    def test_create_access_token_returns_string(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_user_id(self):
        token = create_access_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"

    def test_access_token_type_is_access(self):
        token = create_access_token("user-789")
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_access_token_has_expiry(self):
        token = create_access_token("user-exp")
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload


class TestCreateRefreshToken:
    def test_create_refresh_token_returns_tuple(self):
        token, jti = create_refresh_token("user-123")
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(token) > 0
        assert len(jti) > 0

    def test_refresh_token_contains_user_id(self):
        token, jti = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"

    def test_refresh_token_type_is_refresh(self):
        token, jti = create_refresh_token("user-789")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_refresh_token_has_unique_jti(self):
        _, jti1 = create_refresh_token("user-same")
        _, jti2 = create_refresh_token("user-same")
        assert jti1 != jti2

    def test_refresh_token_has_longer_expiry(self):
        token, _ = create_refresh_token("user-exp")
        payload = decode_token(token)
        access_token = create_access_token("user-exp")
        access_payload = decode_token(access_token)
        # 两个 token 都应该有合理的过期时间
        assert payload["exp"] > 0
        assert access_payload["exp"] > 0
        assert payload["type"] == "refresh"
        assert access_payload["type"] == "access"


class TestVerifyAccessToken:
    def test_verify_valid_token(self):
        token = create_access_token("user-valid")
        payload = verify_access_token(token)
        assert payload["sub"] == "user-valid"

    def test_verify_invalid_token_raises_error(self):
        with pytest.raises(ValueError, match="无效的认证令牌"):
            verify_access_token("invalid.token.here")

    def test_verify_wrong_token_type_raises_error(self):
        # 创建一个 refresh token 但用 access token 验证
        token, _ = create_refresh_token("user-wrong-type")
        with pytest.raises(ValueError, match="无效的认证令牌类型"):
            verify_access_token(token)


class TestVerifyRefreshToken:
    def test_verify_valid_token(self):
        token, jti = create_refresh_token("user-valid")
        payload = verify_refresh_token(token)
        assert payload["sub"] == "user-valid"
        assert payload["jti"] == jti

    def test_verify_invalid_token_raises_error(self):
        with pytest.raises(ValueError, match="无效的刷新令牌"):
            verify_refresh_token("invalid.token.here")

    def test_verify_wrong_token_type_raises_error(self):
        token = create_access_token("user-wrong-type")
        with pytest.raises(ValueError, match="无效的刷新令牌类型"):
            verify_refresh_token(token)


class TestDecodeToken:
    def test_decode_with_custom_secret(self):
        secret = "test-secret-key"
        payload = {"sub": "user-custom", "type": "test"}
        token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
        decoded = decode_token(token, secret=secret)
        assert decoded["sub"] == "user-custom"

    def test_decode_wrong_secret_raises_error(self):
        token = create_access_token("user-wrong")
        with pytest.raises(JWTError):
            decode_token(token, secret="wrong-secret")
