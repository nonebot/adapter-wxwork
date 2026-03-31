from typing import Any

from pydantic import BaseModel, Field


class WsHeaders(BaseModel):
    req_id: str = ""


class WsEnvelope(BaseModel):
    """WebSocket 消息信封：所有 WS 收发消息的顶层结构。"""

    cmd: str = ""
    headers: WsHeaders = Field(default_factory=WsHeaders)
    body: dict[str, Any] = Field(default_factory=dict)
    errcode: int | None = None
    errmsg: str = ""


class WsFrom(BaseModel):
    userid: str = ""


class WsTextContent(BaseModel):
    """文本消息内容。"""

    content: str = ""


class WsImageContent(BaseModel):
    """图片消息内容（长连接模式含 aeskey 用于解密）。"""

    url: str = ""
    aeskey: str = ""


class WsVoiceContent(BaseModel):
    """语音消息内容（长连接模式下已转为文本）。"""

    content: str = ""


class WsFileContent(BaseModel):
    """文件消息内容。"""

    url: str = ""
    aeskey: str = ""


class WsVideoContent(BaseModel):
    """视频消息内容。"""

    url: str = ""
    aeskey: str = ""


class WsMixedItem(BaseModel):
    """图文混排消息中的单个条目。"""

    msgtype: str = ""
    text: WsTextContent | None = None
    image: WsImageContent | None = None


class WsMixedContent(BaseModel):
    """图文混排消息内容。"""

    msg_item: list[WsMixedItem] = Field(default_factory=list)


class WsMsgCallbackBody(BaseModel):
    """aibot_msg_callback 的 body 部分。"""

    aibotid: str = ""
    chatid: str = ""
    chattype: str = "single"
    msgid: str = ""
    msgtype: str = ""
    from_user: WsFrom = Field(default_factory=WsFrom, alias="from")

    # 各消息类型内容（按 msgtype 只有对应字段非 None）
    text: WsTextContent | None = None
    image: WsImageContent | None = None
    voice: WsVoiceContent | None = None
    file: WsFileContent | None = None
    video: WsVideoContent | None = None
    mixed: WsMixedContent | None = None

    model_config = {"populate_by_name": True}


class WsEventDetail(BaseModel):
    eventtype: str = ""


class WsEventCallbackBody(BaseModel):
    """aibot_event_callback 的 body 部分。"""

    aibotid: str = ""
    chatid: str = ""
    chattype: str = "single"
    msgid: str = ""
    create_time: int = 0
    from_user: WsFrom = Field(default_factory=WsFrom, alias="from")
    event: WsEventDetail = Field(default_factory=WsEventDetail)

    model_config = {"populate_by_name": True}


class AccessTokenResponse(BaseModel):
    """gettoken 接口返回。"""

    errcode: int = 0
    errmsg: str = ""
    access_token: str = ""
    expires_in: int = 7200


class ApiResponse(BaseModel):
    """通用 API 响应，仅用于 errcode 检查。"""

    errcode: int = 0
    errmsg: str = ""
