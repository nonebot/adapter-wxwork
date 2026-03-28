"""企业微信协议 Message / MessageSegment 实现。"""

from collections.abc import Iterable
from typing import Any, Union
from typing_extensions import override

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment


class MessageSegment(BaseMessageSegment["Message"]):
    """企业微信协议 MessageSegment。

    支持的消息段类型（对应发送时的 msgtype）：
    - text: 文本
    - image: 图片
    - voice: 语音
    - video: 视频
    - location: 位置
    - link: 链接
    - markdown: Markdown（发送 API）
    - file: 文件（发送 API）
    """

    @classmethod
    @override
    def get_message_class(cls) -> type["Message"]:
        return Message

    @override
    def is_text(self) -> bool:
        return self.type == "text"

    @override
    def __str__(self) -> str:
        if self.is_text():
            return self.data.get("text", "")
        if self.type == "voice":
            return self.data.get("content", "")
        return ""

    @override
    def __add__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return Message(self) + (
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return (
            MessageSegment.text(other) if isinstance(other, str) else Message(other)
        ) + self

    # ------------------------------------------------------------------
    # 接收消息段工厂
    # ------------------------------------------------------------------

    @staticmethod
    def text(text: str) -> "MessageSegment":
        return MessageSegment("text", {"text": str(text)})

    @staticmethod
    def image(
        media_id: str = "",
        pic_url: str = "",
        *,
        url: str = "",
        aeskey: str = "",
    ) -> "MessageSegment":
        return MessageSegment(
            "image",
            {"media_id": media_id, "pic_url": pic_url, "url": url, "aeskey": aeskey},
        )

    @staticmethod
    def voice(
        media_id: str = "", fmt: str = "", *, content: str = ""
    ) -> "MessageSegment":
        return MessageSegment(
            "voice", {"media_id": media_id, "format": fmt, "content": content}
        )

    @staticmethod
    def video(
        media_id: str = "",
        thumb_media_id: str = "",
        *,
        url: str = "",
        aeskey: str = "",
    ) -> "MessageSegment":
        return MessageSegment(
            "video",
            {
                "media_id": media_id,
                "thumb_media_id": thumb_media_id,
                "url": url,
                "aeskey": aeskey,
            },
        )

    @staticmethod
    def file(url: str = "", *, media_id: str = "", aeskey: str = "") -> "MessageSegment":
        """文件消息。"""
        return MessageSegment(
            "file", {"url": url, "media_id": media_id, "aeskey": aeskey}
        )

    @staticmethod
    def location(
        latitude: float, longitude: float, scale: int = 0, label: str = ""
    ) -> "MessageSegment":
        return MessageSegment(
            "location",
            {
                "latitude": latitude,
                "longitude": longitude,
                "scale": scale,
                "label": label,
            },
        )

    @staticmethod
    def link(
        title: str, description: str, url: str, pic_url: str = ""
    ) -> "MessageSegment":
        return MessageSegment(
            "link",
            {
                "title": title,
                "description": description,
                "url": url,
                "pic_url": pic_url,
            },
        )

    # ------------------------------------------------------------------
    # 发送消息段工厂（对应企业微信发送 API 的消息类型）
    # ------------------------------------------------------------------

    @staticmethod
    def markdown(content: str) -> "MessageSegment":
        return MessageSegment("markdown", {"content": content})

    @staticmethod
    def send_image(media_id: str) -> "MessageSegment":
        """发送图片消息（需先上传素材获取 media_id）。"""
        return MessageSegment("send_image", {"media_id": media_id})

    @staticmethod
    def send_voice(media_id: str) -> "MessageSegment":
        """发送语音消息。"""
        return MessageSegment("send_voice", {"media_id": media_id})

    @staticmethod
    def send_video(
        media_id: str, title: str = "", description: str = ""
    ) -> "MessageSegment":
        """发送视频消息。"""
        return MessageSegment(
            "send_video",
            {"media_id": media_id, "title": title, "description": description},
        )

    def to_send_data(self) -> dict[str, Any]:
        """将 MessageSegment 转换为企业微信发送 API 的请求体字段。"""
        if self.type == "text":
            return {"msgtype": "text", "text": {"content": self.data["text"]}}
        if self.type == "markdown":
            return {
                "msgtype": "markdown",
                "markdown": {"content": self.data["content"]},
            }
        if self.type in ("send_image", "image"):
            return {"msgtype": "image", "image": {"media_id": self.data["media_id"]}}
        if self.type in ("send_voice", "voice"):
            return {"msgtype": "voice", "voice": {"media_id": self.data["media_id"]}}
        if self.type in ("send_video", "video"):
            return {
                "msgtype": "video",
                "video": {
                    "media_id": self.data["media_id"],
                    "title": self.data.get("title", ""),
                    "description": self.data.get("description", ""),
                },
            }
        if self.type == "file":
            return {"msgtype": "file", "file": {"media_id": self.data["media_id"]}}
        return {}


class Message(BaseMessage[MessageSegment]):
    """企业微信协议 Message。"""

    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        return MessageSegment

    @override
    def __add__(
        self, other: str | MessageSegment | Iterable[MessageSegment]
    ) -> "Message":
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: str | MessageSegment | Iterable[MessageSegment]
    ) -> "Message":
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(msg)

    @override
    def extract_plain_text(self) -> str:
        return "".join(str(seg) for seg in self if seg.is_text())
