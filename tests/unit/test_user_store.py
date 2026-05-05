"""UserStore 测试"""

import pytest
import bcrypt

from pm_workstation.auth.user_store import hash_password, verify_password


class TestHashPassword:
    def test_hash_returns_string(self):
        hashed = hash_password("testpassword123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_different_each_time(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # bcrypt 使用随机 salt

    def test_hash_does_not_store_plain_password(self):
        hashed = hash_password("mysecret")
        assert "mysecret" not in hashed


class TestVerifyPassword:
    def test_correct_password_verifies(self):
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_fails(self):
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_case_sensitive(self):
        hashed = hash_password("Password123")
        assert verify_password("password123", hashed) is False


class TestPasswordSecurity:
    def test_bcrypt_hash_format(self):
        hashed = hash_password("test1234")
        assert hashed.startswith("$2")  # bcrypt hash prefix

    def test_long_password(self):
        long_pwd = "a" * 100
        hashed = hash_password(long_pwd)
        assert verify_password(long_pwd, hashed) is True
