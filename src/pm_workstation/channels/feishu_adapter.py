"""飞书机器人渠道适配器

支持飞书自建应用机器人，通过 Webhook 接收事件回调，通过 API 回复消息。
文档: https://open.feishu.cn/document/server-docs/im-v1/message-events/message-received
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from pm_workstation.channels.base_adapter import ChannelAdapter
from pm_workstation.channels.models import ChannelConfig, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class FeishuAdapter(ChannelAdapter):
    """飞书机器人适配器
    
    功能：
    - tenant_access_token 自动获取和刷新
    - 支持文本、图片、文件、卡片消息
    - 消息回复和主动推送
    - 签名验证
    - 连接测试
    """

    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.app_id = config.config.get("app_id", "")
        self.app_secret = config.config.get("app_secret", "")
        self.verification_token = config.config.get("verification_token", "")
        self.encrypt_key = config.config.get("encrypt_key", "")
        self._tenant_access_token: str = ""
        self._token_expires: float = 0
        self._http_client: httpx.AsyncClient | None = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def validate_config(self) -> tuple[bool, str]:
        if not self.app_id:
            return False, "缺少 App ID"
        if not self.app_secret:
            return False, "缺少 App Secret"
        if not self.verification_token:
            return False, "缺少 Verification Token"
        return True, ""

    def get_webhook_url_hint(self) -> str:
        return f"/api/v1/channels/{self.config.id}/webhook"

    async def test_connection(self) -> tuple[bool, str]:
        """测试飞书连接是否正常
        
        Returns:
            tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            token = await self._get_tenant_access_token()

            url = "https://open.feishu.cn/open-apis/application/v1/app/info"
            headers = {"Authorization": f"Bearer {token}"}

            resp = await self.http_client.get(url, headers=headers)
            data = resp.json()

            if data.get("code") == 0:
                app_info = data.get("data", {})
                return True, f"连接成功: {app_info.get('name', '飞书应用')}"
            else:
                return False, f"API错误: {data.get('msg', '未知错误')}"

        except httpx.TimeoutException:
            return False, "连接超时，请检查网络"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    async def validate_webhook(self, request_data: dict[str, Any], headers: dict[str, str] = {}) -> dict[str, Any] | None:
        challenge = request_data.get("challenge")
        token = request_data.get("token")

        if challenge and token:
            if token == self.verification_token:
                return {"challenge": challenge}
            logger.warning("[Feishu] Verification token mismatch")
            return None

        if self.encrypt_key:
            if not self._verify_signature(headers, request_data):
                logger.warning("[Feishu] Signature verification failed")
                return None

        return {}

    def _verify_signature(self, headers: dict[str, str], body: dict) -> bool:
        timestamp = headers.get("x-lark-request-timestamp", "")
        nonce = headers.get("x-lark-request-nonce", "")
        signature = headers.get("x-lark-signature", "")

        if not timestamp or not signature:
            return True

        if abs(time.time() - int(timestamp)) > 300:
            return False

        content = timestamp + nonce + self.verification_token
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        content += body_str

        expected = hmac.new(
            self.verification_token.encode(),
            content.encode(),
            hashlib.sha256,
        ).digest()

        return hmac.compare_digest(base64.b64encode(expected).decode(), signature)

    async def parse_incoming(self, request_data: dict[str, Any], headers: dict[str, str] = {}) -> IncomingMessage | None:
        event = request_data.get("event", {})
        if not event:
            return None

        event_type = request_data.get("type", "")

        if event_type == "im.message":
            return await self._parse_message_event(event)
        elif event_type == "im.message.reaction.created":
            return await self._parse_reaction_event(event)

        logger.info(f"[Feishu] Unhandled event type: {event_type}")
        return None

    async def _parse_message_event(self, event: dict) -> IncomingMessage | None:
        """解析消息事件"""
        msg_type = event.get("message", {}).get("message_type", "")

        if msg_type == "text":
            return await self._parse_text_message(event)
        elif msg_type == "image":
            return await self._parse_image_message(event)
        elif msg_type == "file":
            return await self._parse_file_message(event)
        elif msg_type == "interactive":
            return await self._parse_card_message(event)
        else:
            logger.info(f"[Feishu] Skipping message type: {msg_type}")
            return None

    async def _parse_text_message(self, event: dict) -> IncomingMessage | None:
        """解析文本消息"""
        chat_id = event.get("message", {}).get("chat_id", "")
        message_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
        user_name = event.get("sender", {}).get("sender_id", {}).get("name", "")

        content_str = event.get("message", {}).get("content", "{}")
        try:
            content_data = json.loads(content_str)
            text = content_data.get("text", "")
        except json.JSONDecodeError:
            text = content_str

        import re
        text = re.sub(r"@_user_\d+", "", text).strip()

        if not text:
            return None

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=user_id,
            user_name=user_name,
            content=text,
            raw_event=event,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _parse_image_message(self, event: dict) -> IncomingMessage | None:
        """解析图片消息"""
        chat_id = event.get("message", {}).get("chat_id", "")
        message_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
        user_name = event.get("sender", {}).get("sender_id", {}).get("name", "")

        content_str = event.get("message", {}).get("content", "{}")
        try:
            content_data = json.loads(content_str)
            image_key = content_data.get("image_key", "")
        except json.JSONDecodeError:
            image_key = ""

        if not image_key:
            return None

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=user_id,
            user_name=user_name,
            content=f"[图片消息: {image_key}]",
            raw_event=event,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _parse_file_message(self, event: dict) -> IncomingMessage | None:
        """解析文件消息"""
        chat_id = event.get("message", {}).get("chat_id", "")
        message_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
        user_name = event.get("sender", {}).get("sender_id", {}).get("name", "")

        content_str = event.get("message", {}).get("content", "{}")
        try:
            content_data = json.loads(content_str)
            file_key = content_data.get("file_key", "")
            file_name = content_data.get("file_name", "未知文件")
        except json.JSONDecodeError:
            file_key = ""
            file_name = "未知文件"

        if not file_key:
            return None

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=user_id,
            user_name=user_name,
            content=f"[文件: {file_name}]",
            raw_event=event,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _parse_card_message(self, event: dict) -> IncomingMessage | None:
        """解析卡片消息（交互式）"""
        chat_id = event.get("message", {}).get("chat_id", "")
        message_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
        user_name = event.get("sender", {}).get("sender_id", {}).get("name", "")

        content_str = event.get("message", {}).get("content", "{}")
        try:
            content_data = json.loads(content_str)
            callback_id = content_data.get("callback_id", "")
        except json.JSONDecodeError:
            callback_id = ""

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=user_id,
            user_name=user_name,
            content=f"[卡片交互: {callback_id}]",
            raw_event=event,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _parse_reaction_event(self, event: dict) -> IncomingMessage | None:
        """解析表情回应事件"""
        chat_id = event.get("message", {}).get("chat_id", "")
        message_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("operator", {}).get("user_id", "")
        reaction_type = event.get("reaction_type", {}).get("emoji_type", "")

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=user_id,
            user_name="",
            content=f"[表情回应: {reaction_type}]",
            raw_event=event,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """获取 tenant_access_token
        
        Args:
            force_refresh: 强制刷新 token
        """
        if not force_refresh and self._tenant_access_token and time.time() < self._token_expires:
            return self._tenant_access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}

        resp = await self.http_client.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            logger.error(f"[Feishu] Failed to get tenant access token: {data}")
            raise Exception(f"Feishu auth failed: {data.get('msg', '')}")

        self._tenant_access_token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200) - 300
        logger.info("[Feishu] Got new tenant access token")
        return self._tenant_access_token

    async def send_message(self, message: OutgoingMessage) -> bool:
        """发送消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否发送成功
        """
        try:
            token = await self._get_tenant_access_token()
            url = "https://open.feishu.cn/open-apis/im/v1/messages"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            if message.message_id:
                url = f"{url}/{message.message_id}/reply"
                payload = {
                    "msg_type": "text",
                    "content": json.dumps({"text": message.content}, ensure_ascii=False),
                }
            else:
                params = {"receive_id": message.chat_id, "msg_type": "text"}
                payload = {
                    "receive_id": message.chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": message.content}, ensure_ascii=False),
                }

            resp = await self.http_client.post(url, json=payload, headers=headers)
            data = resp.json()

            if data.get("code") != 0:
                logger.error(f"[Feishu] Send message failed: {data}")
                return False

            logger.info(f"[Feishu] Message sent to {message.chat_id}")
            return True

        except Exception as e:
            logger.error(f"[Feishu] Send message error: {e}")
            return False

    async def send_rich_message(
        self,
        receive_id: str,
        content: str,
        msg_type: str = "text",
        message_id: str | None = None,
    ) -> bool:
        """发送富文本消息
        
        Args:
            receive_id: 接收者 ID（用户或群聊）
            content: 消息内容
            msg_type: 消息类型 (text, post, image, file, interactive)
            message_id: 消息ID（用于回复）
            
        Returns:
            bool: 是否发送成功
        """
        try:
            token = await self._get_tenant_access_token()

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            url = "https://open.feishu.cn/open-apis/im/v1/messages"

            if message_id:
                url = f"{url}/{message_id}/reply"

            if msg_type == "text":
                payload = {
                    "receive_id": receive_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": content}, ensure_ascii=False),
                }
            elif msg_type == "interactive":
                payload = {
                    "receive_id": receive_id,
                    "msg_type": "interactive",
                    "content": content,
                }
            else:
                payload = {
                    "receive_id": receive_id,
                    "msg_type": msg_type,
                    "content": content,
                }

            params = {} if message_id else {"receive_id": receive_id}

            resp = await self.http_client.post(
                url,
                json=payload,
                headers=headers,
                params=params if params else None
            )
            data = resp.json()

            if data.get("code") != 0:
                logger.error(f"[Feishu] Send rich message failed: {data}")
                return False

            return True

        except Exception as e:
            logger.error(f"[Feishu] Send rich message error: {e}")
            return False

    async def send_card(
        self,
        receive_id: str,
        card_template: dict,
        message_id: str | None = None,
    ) -> bool:
        """发送卡片消息
        
        Args:
            receive_id: 接收者 ID
            card_template: 卡片模板 JSON
            message_id: 消息ID（用于回复）
            
        Returns:
            bool: 是否发送成功
        """
        return await self.send_rich_message(
            receive_id=receive_id,
            content=json.dumps(card_template, ensure_ascii=False),
            msg_type="interactive",
            message_id=message_id,
        )

    async def upload_image(self, image_path: str) -> str | None:
        """上传图片到飞书
        
        Args:
            image_path: 图片路径或 URL
            
        Returns:
            str: image_key 或 None
        """
        try:
            token = await self._get_tenant_access_token()
            url = "https://open.feishu.cn/open-apis/im/v1/images"

            headers = {
                "Authorization": f"Bearer {token}",
            }

            import pathlib
            file_path = pathlib.Path(image_path)

            if not file_path.exists():
                logger.warning(f"[Feishu] Image file not found: {image_path}")
                return None

            with open(file_path, "rb") as f:
                files = {"image": (file_path.name, f, "image/jpeg")}
                data = {"image_type": "message"}
                resp = await self.http_client.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers
                )

            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {}).get("image_key")

            logger.error(f"[Feishu] Upload image failed: {result}")
            return None

        except Exception as e:
            logger.error(f"[Feishu] Upload image error: {e}")
            return None

    async def get_user_info(self, user_id: str) -> dict | None:
        """获取用户信息
        
        Args:
            user_id: 飞书用户 ID
            
        Returns:
            dict: 用户信息 或 None
        """
        try:
            token = await self._get_tenant_access_token()
            url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}"

            headers = {"Authorization": f"Bearer {token}"}
            resp = await self.http_client.get(url, headers=headers)
            data = resp.json()

            if data.get("code") == 0:
                return data.get("data", {})

            return None

        except Exception as e:
            logger.error(f"[Feishu] Get user info error: {e}")
            return None

    async def get_chat_info(self, chat_id: str) -> dict | None:
        """获取群聊信息
        
        Args:
            chat_id: 飞书群聊 ID
            
        Returns:
            dict: 群聊信息 或 None
        """
        try:
            token = await self._get_tenant_access_token()
            url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}"

            headers = {"Authorization": f"Bearer {token}"}
            resp = await self.http_client.get(url, headers=headers)
            data = resp.json()

            if data.get("code") == 0:
                return data.get("data", {})

            return None

        except Exception as e:
            logger.error(f"[Feishu] Get chat info error: {e}")
            return None
