"""企业微信 Bot 实现。"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from typing_extensions import override

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment
from nonebot.drivers import WebSocket
from nonebot.message import handle_event as handle_event_core

from .config import BotConfig
from .event import Event, WsMsgCallbackEvent
from .message import Message, MessageSegment

if TYPE_CHECKING:
    from .adapter import Adapter


async def _send(
    bot: "Bot",
    event: BaseEvent,
    message: str | BaseMessage | BaseMessageSegment,
    **kwargs: Any,
) -> Any:
    msg = message if isinstance(message, Message) else Message(message)
    if not msg:
        return

    bot_config = bot.bot_config
    # 取第一个 segment 作为发送内容（企业微信每次 send 只能发一条消息）
    # 若需要发多段，逐个调用
    results = []
    for seg in msg:
        assert isinstance(seg, MessageSegment)
        send_data = seg.to_send_data()
        if not send_data:
            continue

        if bot_config.use_ws:
            # WebSocket 模式：通过 aibot_respond_msg 或 aibot_send_msg 发送
            req_id = ""
            chat_id = ""
            chat_type = 1  # 默认单聊

            if isinstance(event, WsMsgCallbackEvent):
                req_id = event.req_id
                chat_id = event.chatid or event.from_userid
                chat_type = 2 if event.chattype == "group" else 1

            if req_id:
                # 回复消息
                result = await bot.call_api(
                    "aibot_respond_msg",
                    __req_id__=req_id,
                    **send_data,
                )
            else:
                # 主动推送
                result = await bot.call_api(
                    "aibot_send_msg",
                    chatid=chat_id,
                    chat_type=chat_type,
                    **send_data,
                )
            results.append(result)
        else:
            # Webhook 模式：使用 REST API 发送消息
            from_user = ""
            agent_id = bot.self_id
            if hasattr(event, "FromUserName"):
                from_user = getattr(event, "FromUserName", "")

            payload = {
                **send_data,
                "touser": kwargs.get("touser", from_user),
                "agentid": kwargs.get("agentid", agent_id),
                "safe": kwargs.get("safe", 0),
            }
            result = await bot.call_api("send_message", **payload)
            results.append(result)

    return results if len(results) > 1 else (results[0] if results else None)


class Bot(BaseBot):
    """企业微信 Bot，支持 Webhook 和 WebSocket 两种模式。"""

    send_handler: Callable[
        ["Bot", BaseEvent, str | BaseMessage | BaseMessageSegment],
        Any,
    ] = _send

    def __init__(self, adapter: "Adapter", self_id: str, *, bot_config: BotConfig):
        super().__init__(adapter, self_id)
        self.bot_config: BotConfig = bot_config
        # WebSocket 连接实例（仅 WS 模式使用）
        self._ws: WebSocket | None = None

    @override
    async def send(
        self,
        event: BaseEvent,
        message: str | BaseMessage | BaseMessageSegment,
        **kwargs: Any,
    ) -> Any:
        return await self.__class__.send_handler(self, event, message, **kwargs)

    @override
    async def call_api(self, api: str, **data: Any) -> Any:
        return await super().call_api(api, **data)

    async def handle_event(self, event: Event) -> None:
        await handle_event_core(cast(BaseBot, self), event)

    # ------------------------------------------------------------------
    # 便捷 API 方法
    # ------------------------------------------------------------------

    async def send_text(
        self,
        touser: str,
        content: str,
        agentid: str | None = None,
    ) -> Any:
        """主动发送文本消息（Webhook 模式）。"""
        return await self.call_api(
            "send_message",
            msgtype="text",
            text={"content": content},
            touser=touser,
            agentid=agentid or self.self_id,
        )

    async def ws_send_msg(
        self,
        chatid: str,
        message: str | Message | MessageSegment,
        chat_type: int = 0,
        req_id: str | None = None,
    ) -> Any:
        """通过 WebSocket 主动推送消息给指定会话（长连接模式）。"""
        msg = message if isinstance(message, Message) else Message(message)
        for seg in msg:
            assert isinstance(seg, MessageSegment)
            send_data = seg.to_send_data()
            if not send_data:
                continue
            if req_id:
                await self.call_api(
                    "aibot_respond_msg",
                    __req_id__=req_id,
                    **send_data,
                )
            else:
                await self.call_api(
                    "aibot_send_msg",
                    chatid=chatid,
                    chat_type=chat_type,
                    **send_data,
                )

    async def ws_respond_welcome(self, req_id: str, message: str | Message) -> Any:
        """回复欢迎语（收到 enter_chat 事件后调用，长连接模式）。"""
        msg = message if isinstance(message, Message) else Message(message)
        for seg in msg:
            assert isinstance(seg, MessageSegment)
            send_data = seg.to_send_data()
            if not send_data:
                continue
            return await self.call_api(
                "aibot_respond_welcome_msg",
                __req_id__=req_id,
                **send_data,
            )
