"""企业微信协议层 Pydantic 模型，用于标准化 JSON 解析。"""

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


class WsMsgCallbackBody(BaseModel):
    """aibot_msg_callback 的 body 部分。"""

    aibotid: str = ""
    chatid: str = ""
    chattype: str = "single"
    msgid: str = ""
    msgtype: str = ""
    from_user: WsFrom = Field(default_factory=WsFrom, alias="from")

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
