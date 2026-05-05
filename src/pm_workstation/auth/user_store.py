"""用户存储模块

提供用户数据的持久化操作，使用 SQLAlchemy 异步模式。
"""

import uuid
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pm_workstation.auth.models import User
from pm_workstation.config import settings


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    salt = bcrypt.gensalt()
    # bcrypt 限制最大 72 字节
    pwd_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配哈希"""
    try:
        # bcrypt 限制最大 72 字节
        pwd_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


class UserStore:
    """用户数据存储"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_user(self, email: str, password: str) -> User:
        """创建新用户

        Args:
            email: 用户邮箱
            password: 明文密码（会自动哈希）

        Returns:
            创建的用户对象
        """
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        """通过邮箱查找用户

        Args:
            email: 用户邮箱

        Returns:
            用户对象，未找到时返回 None
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """通过 ID 查找用户

        Args:
            user_id: 用户唯一标识

        Returns:
            用户对象，未找到时返回 None
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_password(self, user_id: str, new_password: str) -> bool:
        """更新用户密码

        Args:
            user_id: 用户唯一标识
            new_password: 新明文密码

        Returns:
            是否更新成功
        """
        user = await self.find_by_id(user_id)
        if not user:
            return False

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        return True
