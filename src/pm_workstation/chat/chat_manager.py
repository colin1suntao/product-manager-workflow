"""Chat Manager - 会话管理器

管理会话生命周期和消息存储。
"""

import logging
from datetime import datetime

from .chat_models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class ChatManager:
    """会话管理器

    提供会话和消息的 CRUD 操作，使用内存存储（生产环境应使用数据库）。
    """

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    async def create_session(self, user_id: str, title: str | None = None) -> ChatSession:
        """创建新会话

        Args:
            user_id: 用户 ID
            title: 会话标题（可选）

        Returns:
            新创建的会话对象
        """
        session = ChatSession(
            user_id=user_id,
            title=title or "新会话",
        )
        self._sessions[session.id] = session
        self._messages[session.id] = []
        logger.info(f"Created chat session {session.id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        """获取会话详情

        Args:
            session_id: 会话 ID

        Returns:
            会话对象，如果不存在返回 None
        """
        return self._sessions.get(session_id)

    async def list_sessions(self, user_id: str) -> list[ChatSession]:
        """获取用户的会话列表

        Args:
            user_id: 用户 ID

        Returns:
            会话列表，按更新时间倒序排列
        """
        sessions = [
            s for s in self._sessions.values()
            if s.user_id == user_id
        ]
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def update_session(self, session_id: str, **kwargs) -> ChatSession | None:
        """更新会话信息

        Args:
            session_id: 会话 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的会话对象，如果不存在返回 None
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.now()
        return session

    async def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]
        self._messages.pop(session_id, None)
        logger.info(f"Deleted chat session {session_id}")
        return True

    async def add_message(self, session_id: str, message: ChatMessage) -> ChatMessage | None:
        """添加消息到会话

        Args:
            session_id: 会话 ID
            message: 消息对象

        Returns:
            添加的消息，如果会话不存在返回 None
        """
        if session_id not in self._sessions:
            return None

        message.session_id = session_id
        self._messages[session_id].append(message)

        # 更新会话的更新时间
        self._sessions[session_id].updated_at = datetime.now()

        # 如果是第一条用户消息，使用其内容作为会话标题
        if message.role == "user" and len(self._messages[session_id]) == 1:
            title = message.content[:50] + ("..." if len(message.content) > 50 else "")
            self._sessions[session_id].title = title

        return message

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        """获取会话的消息历史

        Args:
            session_id: 会话 ID

        Returns:
            消息列表
        """
        return self._messages.get(session_id, [])

    async def get_message(self, session_id: str, message_id: str) -> ChatMessage | None:
        """获取单条消息

        Args:
            session_id: 会话 ID
            message_id: 消息 ID

        Returns:
            消息对象，如果不存在返回 None
        """
        messages = self._messages.get(session_id, [])
        for msg in messages:
            if msg.id == message_id:
                return msg
        return None

    async def get_context_messages(
        self, session_id: str, limit: int = 10
    ) -> list[ChatMessage]:
        """获取上下文消息（最近 N 条）

        Args:
            session_id: 会话 ID
            limit: 消息数量限制

        Returns:
            最近的消息列表
        """
        messages = self._messages.get(session_id, [])
        return messages[-limit:] if len(messages) > limit else messages

    async def _delete_message(self, session_id: str, message_id: str) -> bool:
        """删除单条消息（内部方法）

        Args:
            session_id: 会话 ID
            message_id: 消息 ID

        Returns:
            是否删除成功
        """
        messages = self._messages.get(session_id, [])
        for i, msg in enumerate(messages):
            if msg.id == message_id:
                messages.pop(i)
                return True
        return False
