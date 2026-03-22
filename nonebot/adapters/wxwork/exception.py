from typing import Any

from nonebot.exception import ActionFailed as BaseActionFailed
from nonebot.exception import AdapterException
from nonebot.exception import ApiNotAvailable as BaseApiNotAvailable
from nonebot.exception import NetworkError as BaseNetworkError


class WxWorkAdapterException(AdapterException):
    def __init__(self):
        super().__init__("wxwork")


class ActionFailed(BaseActionFailed, WxWorkAdapterException):
    """
    API 请求返回错误信息。
    """

    def __init__(self, **kwargs: Any):
        super().__init__()
        self.info = kwargs

    def __repr__(self):
        return (
            "<ActionFailed " + ", ".join(f"{k}={v}" for k, v in self.info.items()) + ">"
        )

    def __str__(self) -> str:
        return self.__repr__()


class NetworkError(BaseNetworkError, WxWorkAdapterException):
    """
    网络错误。
    """

    def __init__(self, msg: str | None = None):
        super().__init__()
        self.msg = msg

    def __repr__(self) -> str:
        return f"<NetworkError {self.msg!r}>"

    def __str__(self) -> str:
        return self.__repr__()


class ApiNotAvailable(BaseApiNotAvailable, WxWorkAdapterException):
    pass
