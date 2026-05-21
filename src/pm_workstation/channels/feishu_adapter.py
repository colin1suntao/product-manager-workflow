"""飞书机器人渠道适配器

支持飞书自建应用机器人，通过 Webhook 接收事件回调，通过 API 回复消息。
文档: https://open.feishu.cn/document/server-docs/im-v1/message-events/message-received
"""

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
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.app_id = config.config.get("app_id", "")
        self.app_secret = config.config.get("app_secret", "")
        self.verification_token = config.config.get("verification_token", "")
        self.encrypt_key = config.config.get("encrypt_key", "")
        self._tenant_access_token: str = ""
        self._token_expires: float = 0

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

        import base64
        return hmac.compare_digest(base64.b64encode(expected).decode(), signature)

    async def parse_incoming(self, request_data: dict[str, Any], headers: dict[str, str] = {}) -> IncomingMessage | None:
        event = request_data.get("event", {})
        if not event:
            return None

        msg_type = event.get("message", {}).get("message_type", "")
        if msg_type != "text":
            logger.info(f"[Feishu] Skipping non-text message type: {msg_type}")
            return None

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

        # Remove @bot mentions
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
            raw_event=request_data,
            message_id=message_id,
            chat_id=chat_id,
        )

    async def _get_tenant_access_token(self) -> str:
        if self._tenant_access_token and time.time() < self._token_expires:
            return self._tenant_access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        if data.get("code") != 0:
            logger.error(f"[Feishu] Failed to get tenant access token: {data}")
            raise Exception(f"Feishu auth failed: {data.get('msg', '')}")

        self._tenant_access_token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200) - 300
        return self._tenant_access_token

    async def send_message(self, message: OutgoingMessage) -> bool:
        try:
            token = await self._get_tenant_access_token()
            url = "https://open.feishu.cn/open-apis/im/v1/messages"

            params = {}
            if message.message_id:
                url = f"{url}/{message.message_id}/reply"
            else:
                params["receive_id"] = message.chat_id
                params["msg_type"] = "text"

            payload = {
                "msg_type": "text",
                "content": json.dumps({"text": message.content}, ensure_ascii=False),
            }

            if not message.message_id:
                payload["receive_id"] = message.chat_id
                payload["msg_type"] = "text"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=15) as client:
                if message.message_id:
                    resp = await client.post(url, json=payload, headers=headers)
                else:
                    resp = await client.post(url, json=payload, headers=headers, params=params)

                data = resp.json()

            if data.get("code") != 0:
                logger.error(f"[Feishu] Send message failed: {data}")
                return False

            return True

        except Exception as e:
            logger.error(f"[Feishu] Send message error: {e}")
            return False
