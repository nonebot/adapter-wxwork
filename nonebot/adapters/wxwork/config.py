"""企业微信适配器配置。"""

from pydantic import BaseModel, Field, HttpUrl


class BotConfig(BaseModel):
    """
    企业微信适配器单机器人配置。

    Webhook（短连接）模式配置：
    - ``corpid``: 企业 ID（管理后台「我的企业」）
    - ``corpsecret``: 应用 Secret（自建应用「Secret」）
    - ``agent_id``: 应用 AgentId
    - ``token``: 接收消息回调配置的 Token
    - ``encoding_aes_key``: 接收消息回调配置的 EncodingAESKey

    WebSocket（长连接）模式配置：
    - ``bot_id``: 智能机器人的 BotID
    - ``secret``: 长连接专用密钥 Secret
    - ``use_ws``: 是否使用长连接模式（默认 False）
    """

    # Webhook 模式
    corpid: str = ""
    corpsecret: str = ""
    agent_id: str = ""
    token: str = ""
    encoding_aes_key: str | None = None

    # WebSocket 长连接模式
    bot_id: str = ""
    secret: str = ""
    use_ws: bool = False

    api_base: HttpUrl | None = Field(
        default=None, description="API 根地址，默认 https://qyapi.weixin.qq.com"
    )

    @property
    def self_id(self) -> str:
        """返回机器人的唯一标识：WS 模式用 bot_id，Webhook 模式用 agent_id。"""
        return self.bot_id if self.use_ws else self.agent_id


class Config(BaseModel):
    """
    企业微信适配器全局配置。

    - ``wxwork_api_base``: 企业微信 API Endpoint
    - ``wxwork_bots``: 多机器人配置列表
    """

    wxwork_api_base: HttpUrl = Field(HttpUrl("https://qyapi.weixin.qq.com"))
    wxwork_bots: list[BotConfig] = Field(default_factory=list)
