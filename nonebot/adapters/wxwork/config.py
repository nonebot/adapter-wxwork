"""企业微信适配器配置。"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, HttpUrl


class BotConfig(BaseModel, ABC):
    """单机器人公共配置（与 ``Config`` 全局项组合使用）。"""

    api_base: HttpUrl | None = Field(
        default=None,
        description="REST API 根地址；为 None 时使用全局 ``wxwork_api_base``",
    )

    @property
    @abstractmethod
    def self_id(self) -> str:
        """机器人唯一标识：Webhook 为 ``agent_id``，WS 为 ``bot_id``。"""
        raise NotImplementedError


class WebhookBotConfig(BotConfig):
    """Webhook（短连接）单机器人配置。

    - ``corpid``: 企业 ID（管理后台「我的企业」）
    - ``corpsecret``: 应用 Secret（自建应用「Secret」）
    - ``agent_id``: 应用 AgentId
    - ``token``: 接收消息回调配置的 Token
    - ``encoding_aes_key``: 接收消息回调配置的 EncodingAESKey
    """

    corpid: str = ""
    corpsecret: str = ""
    agent_id: str = ""
    token: str = ""
    encoding_aes_key: str | None = None

    @property
    def self_id(self) -> str:
        return self.agent_id


class WsBotConfig(BotConfig):
    """WebSocket（长连接 / 智能机器人）单机器人配置。

    - ``bot_id``: 智能机器人的 BotID
    - ``secret``: 长连接专用密钥 Secret
    """

    bot_id: str = ""
    secret: str = ""

    @property
    def self_id(self) -> str:
        return self.bot_id


class Config(BaseModel):
    """
    企业微信适配器全局配置。

    - ``wxwork_api_base``: 全局默认 REST API 根地址（单机器人可在 ``api_base`` 覆盖）
    - ``wxwork_ws_url``: WebSocket 长连接地址（默认官方 openws）
    - ``wxwork_webhook_bots``: Webhook 模式机器人列表
    - ``wxwork_ws_bots``: WebSocket 长连接模式机器人列表
    """

    wxwork_api_base: str = "https://qyapi.weixin.qq.com"
    wxwork_ws_url: str = "wss://openws.work.weixin.qq.com"
    wxwork_webhook_bots: list[WebhookBotConfig] = Field(default_factory=list)
    wxwork_ws_bots: list[WsBotConfig] = Field(default_factory=list)
