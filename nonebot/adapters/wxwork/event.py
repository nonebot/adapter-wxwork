from typing import Any, Literal
from typing_extensions import override

from pydantic import Field

from nonebot.adapters import Event as BaseEvent
from nonebot.compat import type_validate_python
from nonebot.utils import escape_tag

from .message import Message, MessageSegment
from .models import WsEnvelope, WsEventCallbackBody, WsMsgCallbackBody
from .utils import log


class Event(BaseEvent):
    __event__: str = ""

    @override
    def get_type(self) -> str:
        return "meta"

    @override
    def get_event_name(self) -> str:
        return self.__class__.__name__

    @override
    def get_event_description(self) -> str:
        return escape_tag(repr(self))

    @override
    def get_message(self) -> Message:
        raise ValueError("Event has no message!")

    @override
    def get_plaintext(self) -> str:
        raise ValueError("Event has no plaintext!")

    @override
    def get_user_id(self) -> str:
        raise ValueError("Event has no user_id!")

    @override
    def get_session_id(self) -> str:
        raise ValueError("Event has no session_id!")

    @override
    def is_tome(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Webhook 普通消息
# ---------------------------------------------------------------------------


class MessageEvent(Event):
    """Webhook 模式消息事件基类（XML 解密后的字段）。"""

    __event__ = "message"

    ToUserName: str = ""
    FromUserName: str = ""
    CreateTime: int = 0
    MsgType: str = ""
    MsgId: int = 0
    AgentID: int = 0

    to_me: bool = False

    @override
    def get_type(self) -> Literal["message"]:
        return "message"

    @override
    def get_event_name(self) -> str:
        return f"message.{self.MsgType}"

    @override
    def get_event_description(self) -> str:
        return f"{self.MsgId} from {self.FromUserName}"

    @override
    def get_message(self) -> Message:
        raise ValueError("Subclass must implement get_message()")

    @override
    def get_plaintext(self) -> str:
        return ""

    @override
    def get_user_id(self) -> str:
        return self.FromUserName

    @override
    def get_session_id(self) -> str:
        return f"{self.AgentID}_{self.FromUserName}"

    @override
    def is_tome(self) -> bool:
        return self.to_me


class TextMessageEvent(MessageEvent):
    """文本消息。"""

    __event__ = "message.text"

    MsgType: Literal["text"] = "text"
    Content: str = ""

    @override
    def get_event_description(self) -> str:
        return f"{self.MsgId} from {self.FromUserName}: {escape_tag(self.Content)}"

    @override
    def get_message(self) -> Message:
        return Message(MessageSegment.text(self.Content))

    @override
    def get_plaintext(self) -> str:
        return self.Content


class ImageMessageEvent(MessageEvent):
    """图片消息。"""

    __event__ = "message.image"

    MsgType: Literal["image"] = "image"
    PicUrl: str = ""
    MediaId: str = ""

    @override
    def get_message(self) -> Message:
        return Message(MessageSegment.image(self.MediaId, self.PicUrl))


class VoiceMessageEvent(MessageEvent):
    """语音消息。"""

    __event__ = "message.voice"

    MsgType: Literal["voice"] = "voice"
    MediaId: str = ""
    Format: str = ""

    @override
    def get_message(self) -> Message:
        return Message(MessageSegment.voice(self.MediaId, self.Format))


class VideoMessageEvent(MessageEvent):
    """视频消息。"""

    __event__ = "message.video"

    MsgType: Literal["video"] = "video"
    MediaId: str = ""
    ThumbMediaId: str = ""

    @override
    def get_message(self) -> Message:
        return Message(MessageSegment.video(self.MediaId, self.ThumbMediaId))


class LocationMessageEvent(MessageEvent):
    """位置消息。"""

    __event__ = "message.location"

    MsgType: Literal["location"] = "location"
    Location_X: float = 0.0
    Location_Y: float = 0.0
    Scale: int = 0
    Label: str = ""
    AppType: str = ""

    @override
    def get_message(self) -> Message:
        return Message(
            MessageSegment.location(
                self.Location_X, self.Location_Y, self.Scale, self.Label
            )
        )


class LinkMessageEvent(MessageEvent):
    """链接消息。"""

    __event__ = "message.link"

    MsgType: Literal["link"] = "link"
    Title: str = ""
    Description: str = ""
    Url: str = ""
    PicUrl: str = ""

    @override
    def get_message(self) -> Message:
        return Message(
            MessageSegment.link(self.Title, self.Description, self.Url, self.PicUrl)
        )


# ---------------------------------------------------------------------------
# Webhook 事件消息（MsgType=event）
# ---------------------------------------------------------------------------


class EventMessage(Event):
    """Webhook 模式事件基类（MsgType=event）。"""

    __event__ = "notice"

    ToUserName: str = ""
    FromUserName: str = ""
    CreateTime: int = 0
    MsgType: Literal["event"] = "event"
    Event: str = ""
    AgentID: int = 0

    @override
    def get_type(self) -> Literal["notice"]:
        return "notice"

    @override
    def get_event_name(self) -> str:
        return f"notice.{self.Event}"

    @override
    def get_user_id(self) -> str:
        return self.FromUserName

    @override
    def get_session_id(self) -> str:
        return f"{self.AgentID}_{self.FromUserName}"


class SubscribeEvent(EventMessage):
    """关注/订阅事件。"""

    __event__ = "notice.subscribe"
    Event: Literal["subscribe"] = "subscribe"


class UnsubscribeEvent(EventMessage):
    """取消关注事件。"""

    __event__ = "notice.unsubscribe"
    Event: Literal["unsubscribe"] = "unsubscribe"


class EnterAgentEvent(EventMessage):
    """进入应用事件。"""

    __event__ = "notice.enter_agent"
    Event: Literal["enter_agent"] = "enter_agent"
    EventKey: str = ""


class ClickMenuEvent(EventMessage):
    """点击菜单事件。"""

    __event__ = "notice.click"
    Event: Literal["CLICK"] = "CLICK"
    EventKey: str = ""


class ViewMenuEvent(EventMessage):
    """点击菜单跳转链接事件。"""

    __event__ = "notice.view"
    Event: Literal["VIEW"] = "VIEW"
    EventKey: str = ""


class ScanQREvent(EventMessage):
    """扫码事件。"""

    __event__ = "notice.scancode_push"
    Event: Literal["scancode_push"] = "scancode_push"
    EventKey: str = ""
    ScanCodeInfo: dict | None = None


class LocationSelectEvent(EventMessage):
    """弹出地理位置选择器事件。"""

    __event__ = "notice.location_select"
    Event: Literal["LOCATION"] = "LOCATION"
    Latitude: float = 0.0
    Longitude: float = 0.0
    Precision: float = 0.0


# ---------------------------------------------------------------------------
# WebSocket 长连接事件
# ---------------------------------------------------------------------------


class WsEvent(Event):
    """WebSocket 长连接事件基类。"""

    __event__ = ""

    cmd: str = ""
    req_id: str = ""

    @override
    def get_user_id(self) -> str:
        raise ValueError("Event has no user_id!")

    @override
    def get_session_id(self) -> str:
        raise ValueError("Event has no session_id!")


class WsMsgCallbackEvent(MessageEvent):
    """WebSocket 消息回调（aibot_msg_callback）。

    继承 MessageEvent，与 Webhook 消息共用同一基类，便于插件统一注入 ``MessageEvent``。
    构造时请同步设置 ``FromUserName`` / ``MsgType`` / ``MsgId``（与 Webhook 字段语义一致）。
    """

    cmd: Literal["aibot_msg_callback"] = "aibot_msg_callback"
    req_id: str = ""
    """本条 WS 回调的请求 id，用于 ``aibot_respond_msg``。"""
    msgid: str = ""
    """企业微信侧消息 id（字符串）。"""
    aibotid: str = ""
    chatid: str = ""
    chattype: str = "single"  # single / group
    body: WsMsgCallbackBody = Field(default_factory=WsMsgCallbackBody)
    """解析后的消息体，各消息类型内容由对应字段持有。"""

    to_me: bool = True  # 长连接模式下机器人收到的消息默认认为是 @to_me

    @override
    def get_event_description(self) -> str:
        content = self.get_plaintext()
        return f"{self.msgid} from {self.FromUserName}: {escape_tag(content)}"

    def _parse_message(self) -> Message:
        """将 body 按 msgtype 解析为 Message。"""
        msgtype = self.MsgType
        b = self.body

        if msgtype == "text" and b.text:
            return Message(MessageSegment.text(b.text.content))

        if msgtype == "image" and b.image:
            return Message(MessageSegment.image(url=b.image.url, aeskey=b.image.aeskey))

        if msgtype == "voice" and b.voice:
            return Message(MessageSegment.voice(content=b.voice.content))

        if msgtype == "file" and b.file:
            return Message(MessageSegment.file(url=b.file.url, aeskey=b.file.aeskey))

        if msgtype == "video" and b.video:
            return Message(MessageSegment.video(url=b.video.url, aeskey=b.video.aeskey))

        if msgtype == "mixed" and b.mixed:
            msg = Message()
            for item in b.mixed.msg_item:
                if item.msgtype == "text" and item.text:
                    msg.append(MessageSegment.text(item.text.content))
                elif item.msgtype == "image" and item.image:
                    msg.append(
                        MessageSegment.image(
                            url=item.image.url, aeskey=item.image.aeskey
                        )
                    )
            return msg

        return Message()

    @override
    def get_message(self) -> Message:
        return self._parse_message()

    @override
    def get_plaintext(self) -> str:
        msgtype = self.MsgType
        b = self.body

        if msgtype == "text" and b.text:
            return b.text.content
        if msgtype == "voice" and b.voice:
            return b.voice.content
        if msgtype == "mixed" and b.mixed:
            parts: list[str] = []
            for item in b.mixed.msg_item:
                if item.msgtype == "text" and item.text:
                    parts.append(item.text.content)
            return "".join(parts)
        return ""

    @override
    def get_session_id(self) -> str:
        return self.chatid or self.FromUserName


class WsEventCallbackEvent(EventMessage):
    """WebSocket 事件回调（aibot_event_callback）。

    继承 EventMessage，与 Webhook 的 notice 事件对齐；``Event`` 字段对应 WS 的 ``eventtype``。
    """

    cmd: Literal["aibot_event_callback"] = "aibot_event_callback"
    req_id: str = ""
    msgid: str = ""
    aibotid: str = ""
    chatid: str = ""
    chattype: str = "single"
    body: WsEventCallbackBody = Field(default_factory=WsEventCallbackBody)

    @override
    def get_event_description(self) -> str:
        return f"event={self.Event} from {self.FromUserName}"

    @override
    def get_session_id(self) -> str:
        return self.chatid or self.FromUserName


class WsEnterChatEvent(WsEventCallbackEvent):
    """进入会话事件（enter_chat）。

    用户当天首次进入机器人单聊会话时触发。
    可通过 ``bot.ws_respond_welcome(event.req_id, message)`` 回复欢迎语。
    """

    __event__ = "notice.enter_chat"
    Event: Literal["enter_chat"] = "enter_chat"


class WsTemplateCardEvent(WsEventCallbackEvent):
    """模板卡片事件（template_card_event）。

    用户点击模板卡片按钮时触发。
    ``event_key`` 为用户点击的按钮 key，``task_id`` 为对应的任务 ID。
    """

    __event__ = "notice.template_card_event"
    Event: Literal["template_card_event"] = "template_card_event"
    event_key: str = ""
    task_id: str = ""


class WsFeedbackEvent(WsEventCallbackEvent):
    """用户反馈事件（feedback_event）。

    用户对机器人回复进行反馈时触发。
    """

    __event__ = "notice.feedback_event"
    Event: Literal["feedback_event"] = "feedback_event"


class WsDisconnectedEvent(WsEvent):
    """WebSocket 连接断开事件（disconnected_event）。"""

    __event__ = "ws.disconnected"

    cmd: Literal["aibot_event_callback"] = "aibot_event_callback"
    aibotid: str = ""

    @override
    def get_type(self) -> Literal["meta"]:
        return "meta"

    @override
    def get_event_name(self) -> str:
        return "ws.disconnected"


# ---------------------------------------------------------------------------
# 事件类型注册表（供 Adapter 使用）
# ---------------------------------------------------------------------------

# Webhook 事件：key = "message.{MsgType}" 或 "notice.{Event}"
WEBHOOK_MSG_EVENTS: dict[str, type[MessageEvent]] = {
    "text": TextMessageEvent,
    "image": ImageMessageEvent,
    "voice": VoiceMessageEvent,
    "video": VideoMessageEvent,
    "location": LocationMessageEvent,
    "link": LinkMessageEvent,
}

WEBHOOK_EVENT_EVENTS: dict[str, type[EventMessage]] = {
    "subscribe": SubscribeEvent,
    "unsubscribe": UnsubscribeEvent,
    "enter_agent": EnterAgentEvent,
    "CLICK": ClickMenuEvent,
    "VIEW": ViewMenuEvent,
    "scancode_push": ScanQREvent,
    "LOCATION": LocationSelectEvent,
}

# WebSocket 事件回调：key = eventtype
WS_EVENT_TYPES: dict[str, type[WsEventCallbackEvent]] = {
    "enter_chat": WsEnterChatEvent,
    "template_card_event": WsTemplateCardEvent,
    "feedback_event": WsFeedbackEvent,
}


def xml_to_event(data: dict[str, Any]) -> Event | None:
    """将 Webhook XML 解密后的 dict 转为对应的 Event 实例。"""
    msg_type = data.get("MsgType", "")
    try:
        if msg_type == "event":
            event_type = data.get("Event", "")
            if (event_cls := WEBHOOK_EVENT_EVENTS.get(event_type)) is None:
                return None

            return type_validate_python(event_cls, data)
        else:
            if (event_cls := WEBHOOK_MSG_EVENTS.get(msg_type)) is None:
                return None

            return type_validate_python(event_cls, data)
    except Exception as e:
        log(
            "ERROR",
            f"Failed to parse webhook event. Raw: {escape_tag(str(data))}",
            e,
        )


def ws_to_event(data: dict[str, Any]) -> Event | None:
    """将 WebSocket JSON 消息转为对应的 Event 实例。"""
    try:
        envelope = WsEnvelope.model_validate(data)
        cmd = envelope.cmd
        req_id = envelope.headers.req_id

        if cmd == "aibot_msg_callback":
            body = WsMsgCallbackBody.model_validate(envelope.body)
            msg_id_int = int(body.msgid) if body.msgid.isdigit() else 0

            return WsMsgCallbackEvent(
                cmd=cmd,
                req_id=req_id,
                msgid=body.msgid,
                aibotid=body.aibotid,
                chatid=body.chatid,
                chattype=body.chattype,
                body=body,
                FromUserName=body.from_user.userid,
                MsgType=body.msgtype,
                MsgId=msg_id_int,
                to_me=True,
            )
        elif cmd == "aibot_event_callback":
            body = WsEventCallbackBody.model_validate(envelope.body)
            eventtype = body.event.eventtype
            if eventtype == "disconnected_event":
                return WsDisconnectedEvent(
                    cmd=cmd,
                    req_id=req_id,
                    aibotid=body.aibotid,
                )

            event_cls = WS_EVENT_TYPES.get(eventtype, WsEventCallbackEvent)

            kwargs: dict[str, Any] = {
                "cmd": cmd,
                "req_id": req_id,
                "msgid": body.msgid,
                "aibotid": body.aibotid,
                "chatid": body.chatid,
                "chattype": body.chattype,
                "body": body,
                "FromUserName": body.from_user.userid,
                "CreateTime": body.create_time,
            }

            if event_cls is WsEventCallbackEvent:
                kwargs["Event"] = eventtype
            elif event_cls is WsTemplateCardEvent:
                kwargs["event_key"] = body.event.event_key or ""
                kwargs["task_id"] = body.event.task_id or ""

            return event_cls(**kwargs)

    except Exception as e:
        log("ERROR", f"Failed to parse WS event. Raw: {escape_tag(str(data))}", e)
