from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, HttpUrl


class BotConfig(BaseModel, ABC):
    api_base: HttpUrl | None = Field(default=None)

    @property
    @abstractmethod
    def self_id(self) -> str:
        raise NotImplementedError


class WebhookBotConfig(BotConfig):
    corpid: str = ""
    corpsecret: str = ""
    agent_id: str = ""
    token: str = ""
    encoding_aes_key: str | None = None

    @property
    def self_id(self) -> str:
        return self.agent_id


class WsBotConfig(BotConfig):
    bot_id: str = ""
    secret: str = ""

    @property
    def self_id(self) -> str:
        return self.bot_id


class Config(BaseModel):
    wxwork_api_base: str = "https://qyapi.weixin.qq.com"
    wxwork_ws_url: str = "wss://openws.work.weixin.qq.com"
    wxwork_webhook_bots: list[WebhookBotConfig] = Field(default_factory=list)
    wxwork_ws_bots: list[WsBotConfig] = Field(default_factory=list)
