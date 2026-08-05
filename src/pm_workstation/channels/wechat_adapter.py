"""微信企业机器人渠道适配器

支持企业微信自建应用机器人，通过 Webhook 接收回调，通过 API 回复消息。
文档: https://developer.work.weixin.qq.com/document/path/90236
"""

import logging
import time
from typing import Any

import httpx

from pm_workstation.channels.base_adapter import ChannelAdapter
from pm_workstation.channels.models import ChannelConfig, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WeChatAdapter(ChannelAdapter):
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.corp_id = config.config.get("corp_id", "")
        self.agent_id = config.config.get("agent_id", "")
        self.secret = config.config.get("secret", "")
        self.token = config.config.get("token", "")
        self.encoding_aes_key = config.config.get("encoding_aes_key", "")
        self._access_token: str = ""
        self._token_expires: float = 0

    def validate_config(self) -> tuple[bool, str]:
        if not self.corp_id:
            return False, "缺少企业 ID (Corp ID)"
        if not self.secret:
            return False, "缺少应用 Secret"
        if not self.token:
            return False, "缺少回调 Token"
        return True, ""

    def get_webhook_url_hint(self) -> str:
        return f"/api/v1/channels/{self.config.id}/webhook"

    async def validate_webhook(self, request_data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any] | None:
        echostr = request_data.get("echostr")
        if echostr:
            return {"echostr": echostr}
        return {}

    async def parse_incoming(self, request_data: dict[str, Any], headers: dict[str, str] | None = None) -> IncomingMessage | None:
        content = ""
        from_user = ""
        msg_id = ""
        msg_type = ""

        if isinstance(request_data, dict):
            content = request_data.get("Content", request_data.get("content", ""))
            from_user = request_data.get("FromUserName", request_data.get("from_user_name", ""))
            msg_id = request_data.get("MsgId", request_data.get("msg_id", ""))
            msg_type = request_data.get("MsgType", request_data.get("msg_type", "text"))

        if msg_type and msg_type != "text":
            logger.info(f"[WeChat] Skipping non-text message type: {msg_type}")
            return None

        if not content:
            return None

        chat_id = from_user
        if request_data.get("chatid"):
            chat_id = request_data["chatid"]

        return IncomingMessage(
            channel_id=self.config.id,
            channel_type=self.config.channel_type,
            user_id=from_user,
            user_name=from_user,
            content=content.strip(),
            raw_event=request_data,
            message_id=msg_id,
            chat_id=chat_id,
        )

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()

        if data.get("errcode") != 0:
            logger.error(f"[WeChat] Failed to get access token: {data}")
            raise Exception(f"WeChat auth failed: {data.get('errmsg', '')}")

        self._access_token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300
        return self._access_token

    async def send_message(self, message: OutgoingMessage) -> bool:
        try:
            token = await self._get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

            payload = {
                "touser": message.user_id,
                "msgtype": "text",
                "agentid": int(self.agent_id) if self.agent_id else 0,
                "text": {"content": message.content},
            }

            if message.chat_id and message.chat_id.startswith("wr"):
                payload = {
                    "chatid": message.chat_id,
                    "msgtype": "text",
                    "text": {"content": message.content},
                }
                url = f"https://qyapi.weixin.qq.com/cgi-bin/appchat/send?access_token={token}"

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()

            if data.get("errcode") != 0:
                logger.error(f"[WeChat] Send message failed: {data}")
                return False

            return True

        except Exception as e:
            logger.error(f"[WeChat] Send message error: {e}")
            return False
