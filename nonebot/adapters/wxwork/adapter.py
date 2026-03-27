"""企业微信适配器：支持 Webhook（短连接）和 WebSocket（长连接）两种模式。"""

import asyncio
import json
import time
from typing import Any, cast
from typing_extensions import override
from urllib.parse import urlencode
import uuid

import xmltodict

from nonebot import get_plugin_config
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.compat import type_validate_python
from nonebot.drivers import (
    URL,
    ASGIMixin,
    Driver,
    HTTPClientMixin,
    HTTPServerSetup,
    Request,
    Response,
    WebSocket,
    WebSocketClientMixin,
)
from nonebot.exception import WebSocketClosed
from nonebot.utils import escape_tag

from .bot import Bot
from .config import BotConfig, Config, WebhookBotConfig, WsBotConfig
from .crypto import WxBizMsgCrypt
from .event import (
    WEBHOOK_EVENT_EVENTS,
    WEBHOOK_MSG_EVENTS,
    Event,
    WsDisconnectedEvent,
    WsEventCallbackEvent,
    WsMsgCallbackEvent,
)
from .exception import (
    ActionFailed,
    ApiNotAvailable,
    NetworkError,
    WxWorkAdapterException,
)
from .utils import log

PING_INTERVAL = 30  # seconds
RECONNECT_INTERVAL = 5  # seconds


class Adapter(BaseAdapter):
    """企业微信适配器。支持 Webhook 和 WebSocket（智能机器人长连接）两种模式。"""

    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.wxwork_config: Config = get_plugin_config(Config)
        self.bot_config_by_id: dict[str, BotConfig] = {}
        self.tasks: set[asyncio.Task] = set()
        self._access_tokens: dict[str, tuple[str, float]] = (
            {}
        )  # agent_id -> (token, expire_time)
        self._setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        return "WxWork"

    def _setup(self) -> None:
        if isinstance(self.driver, ASGIMixin):
            self._setup_webhook()

        if (
            self.wxwork_config.wxwork_ws_bots
            and len(self.wxwork_config.wxwork_ws_bots) > 0
        ):
            if not isinstance(self.driver, WebSocketClientMixin):
                log(
                    "WARNING",
                    (
                        f"Current driver {self.config.driver} does not support "
                        "websocket client connections! Ignored"
                    ),
                )
            else:
                self.on_ready(self._start_forward)

        self.driver.on_shutdown(self._stop)

    def _setup_webhook(self) -> None:
        for bot_config in self.wxwork_config.wxwork_webhook_bots:
            self_id = bot_config.self_id
            self.bot_config_by_id[self_id] = bot_config
            if self.bots.get(self_id):
                continue

            for method in ("GET", "POST"):
                setup = HTTPServerSetup(
                    URL(f"/wxwork/{self_id}"),
                    method,
                    self.get_name(),
                    self._handle_http,
                )
                self.setup_http_server(setup)

            bot = Bot(self, self_id, bot_config=bot_config)
            self.bot_connect(bot)
            log("INFO", f"Bot {escape_tag(self_id)} connected")

    async def _start_forward(self) -> None:
        for bot_config in self.wxwork_config.wxwork_ws_bots:
            bot = Bot(self, bot_config.self_id, bot_config=bot_config)
            task = asyncio.create_task(self._forward_ws(bot, bot_config))
            task.add_done_callback(self.tasks.discard)
            self.tasks.add(task)

    async def _stop(self) -> None:
        for task in self.tasks:
            if not task.done():
                task.cancel()

    async def _handle_http(self, request: Request) -> Response:
        """处理企业微信 Webhook 回调（GET 验证 + POST 消息）。"""
        self_id = request.url.parts[-1]
        bot_config = self.bot_config_by_id.get(self_id)
        if bot_config is None or not isinstance(bot_config, WebhookBotConfig):
            return Response(404, content=b"bot not found")

        bot = self.bots.get(self_id)
        if bot is None:
            return Response(500, content=b"bot instance not found")

        msg_signature = request.url.query.get("msg_signature", "")
        timestamp = request.url.query.get("timestamp", "")
        nonce = request.url.query.get("nonce", "")

        if not (bot_config.token and bot_config.encoding_aes_key):
            return Response(400, content=b"missing token or encoding_aes_key")

        crypt = WxBizMsgCrypt(
            bot_config.token,
            bot_config.encoding_aes_key,
            bot_config.corpid,
        )

        # GET: URL 验证
        if request.method == "GET":
            echostr = request.url.query.get("echostr", "")
            try:
                plain = crypt.verify_url(msg_signature, timestamp, nonce, echostr)
            except ActionFailed:
                return Response(403, content=b"invalid signature")
            return Response(200, content=plain.encode())

        # POST: 消息/事件回调
        if not request.content:
            return Response(400, content=b"empty body")

        try:
            xml_data = xmltodict.parse(request.content)
            outer = xml_data.get("xml", {})
            msg_encrypt = outer.get("Encrypt", "")
        except Exception:
            return Response(400, content=b"invalid xml")

        try:
            if not crypt.verify_signature(msg_signature, timestamp, nonce, msg_encrypt):
                return Response(403, content=b"invalid signature")

            decrypted = crypt.decrypt(msg_encrypt)
        except Exception as e:
            log("ERROR", "Failed to decrypt message", e)
            return Response(400, content=b"decrypt failed")

        try:
            msg_data = xmltodict.parse(decrypted).get("xml", {})
        except Exception:
            return Response(400, content=b"invalid decrypted xml")

        event = self._xml_to_event(msg_data)
        if event is not None:
            task = asyncio.create_task(cast(Bot, bot).handle_event(event))
            task.add_done_callback(self.tasks.discard)
            self.tasks.add(task)

        return Response(200, content=b"success")

    @classmethod
    def _xml_to_event(cls, data: dict[str, Any]) -> Event | None:
        msg_type = data.get("MsgType", "")
        try:
            if msg_type == "event":
                event_type = data.get("Event", "")
                event_cls = WEBHOOK_EVENT_EVENTS.get(event_type)
                if event_cls is None:
                    return None
                return type_validate_python(event_cls, data)
            else:
                event_cls = WEBHOOK_MSG_EVENTS.get(msg_type)
                if event_cls is None:
                    return None
                return type_validate_python(event_cls, data)
        except Exception as e:
            log(
                "ERROR",
                f"Failed to parse webhook event. Raw: {escape_tag(str(data))}",
                e,
            )
            return None

    async def _forward_ws(self, bot: "Bot", bot_config: WsBotConfig) -> None:
        """维护单个机器人的 WebSocket 长连接，含断线重连。"""
        url = str(self.wxwork_config.wxwork_ws_url)
        request = Request("GET", URL(url), headers={}, timeout=30.0)

        while True:
            registered = False
            ping_task: asyncio.Task[None] | None = None
            try:
                async with self.websocket(request) as ws:
                    log(
                        "DEBUG",
                        f"WebSocket Connection to {escape_tag(url)} established",
                    )
                    try:
                        bot._ws = ws

                        # 发送订阅请求
                        sub_req_id = str(uuid.uuid4())
                        await ws.send_text(
                            json.dumps(
                                {
                                    "cmd": "aibot_subscribe",
                                    "headers": {"req_id": sub_req_id},
                                    "body": {
                                        "bot_id": bot_config.bot_id,
                                        "secret": bot_config.secret,
                                    },
                                }
                            )
                        )
                        raw = await ws.receive_text()
                        resp = json.loads(raw)
                        if resp.get("errcode", -1) != 0:
                            raise RuntimeError(f"WS subscribe failed: {resp}")
                        log(
                            "INFO",
                            f"Bot {escape_tag(bot_config.bot_id)} WS subscribed",
                        )

                        self.bot_connect(bot)
                        registered = True
                        log(
                            "INFO",
                            f"<y>Bot {escape_tag(bot_config.bot_id)}</y> connected",
                        )

                        ping_task = asyncio.create_task(self._ws_ping_loop(ws))

                        while True:
                            raw_msg = await ws.receive_text()
                            try:
                                data = json.loads(raw_msg)
                            except Exception:
                                continue

                            event = self._ws_to_event(data)
                            if event is None:
                                continue

                            if isinstance(event, WsDisconnectedEvent):
                                log(
                                    "INFO",
                                    f"Bot {escape_tag(bot_config.bot_id)} "
                                    "WS disconnected by server",
                                )
                                break

                            task = asyncio.create_task(bot.handle_event(event))
                            task.add_done_callback(self.tasks.discard)
                            self.tasks.add(task)
                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>"
                            "Error while process data from websocket "
                            f"{escape_tag(url)}. Trying to reconnect..."
                            "</bg #f8bbd0></r>",
                            e,
                        )
                    finally:
                        if ping_task is not None:
                            ping_task.cancel()
                        bot._ws = None
                        if registered:
                            self.bot_disconnect(bot)

            except Exception as e:
                log(
                    "ERROR",
                    "<r><bg #f8bbd0>Error while setup websocket to "
                    f"{escape_tag(url)}. Trying to reconnect...</bg #f8bbd0></r>",
                    e,
                )

            await asyncio.sleep(RECONNECT_INTERVAL)

    async def _ws_ping_loop(self, ws: WebSocket) -> None:
        """发送应用层心跳：订阅成功后立即发一次，之后每 PING_INTERVAL 秒一次。

        若先 sleep 再发首包，服务端可能在第 30 秒空闲超时关连接，与首条 ping 撞车。
        """
        while True:
            try:
                await ws.send_text(
                    json.dumps(
                        {
                            "cmd": "ping",
                            "headers": {"req_id": str(uuid.uuid4())},
                        }
                    )
                )
            except Exception:
                break
            await asyncio.sleep(PING_INTERVAL)

    @classmethod
    def _ws_to_event(cls, data: dict[str, Any]) -> Event | None:
        cmd = data.get("cmd", "")
        headers = data.get("headers", {})
        req_id = headers.get("req_id", "")
        body = data.get("body", {})

        try:
            if cmd == "aibot_msg_callback":
                from_uid = body.get("from", {}).get("userid", "")
                msgid_str = body.get("msgid", "")
                msgtype = body.get("msgtype", "")
                msg_id_int = int(msgid_str) if msgid_str.isdigit() else 0
                event = WsMsgCallbackEvent(
                    cmd=cmd,
                    req_id=req_id,
                    msgid=msgid_str,
                    aibotid=body.get("aibotid", ""),
                    chatid=body.get("chatid", ""),
                    chattype=body.get("chattype", "single"),
                    raw_body=body,
                    FromUserName=from_uid,
                    MsgType=msgtype,
                    MsgId=msg_id_int,
                    to_me=True,
                )
                return event
            elif cmd == "aibot_event_callback":
                event_body = body.get("event", {})
                eventtype = event_body.get("eventtype", "")
                if eventtype == "disconnected_event":
                    return WsDisconnectedEvent(
                        cmd=cmd,
                        req_id=req_id,
                        aibotid=body.get("aibotid", ""),
                    )
                ct = body.get("create_time", 0)
                try:
                    create_time_int = int(ct) if ct is not None else 0
                except (TypeError, ValueError):
                    create_time_int = 0
                return WsEventCallbackEvent(
                    cmd=cmd,
                    req_id=req_id,
                    msgid=body.get("msgid", ""),
                    aibotid=body.get("aibotid", ""),
                    chatid=body.get("chatid", ""),
                    chattype=body.get("chattype", "single"),
                    raw_body=body,
                    FromUserName=body.get("from", {}).get("userid", ""),
                    Event=eventtype,
                    CreateTime=create_time_int,
                )
        except Exception as e:
            log("ERROR", f"Failed to parse WS event. Raw: {escape_tag(str(data))}", e)
        return None

    # ------------------------------------------------------------------
    # API 调用（Webhook 模式：发送消息 via REST API）
    # ------------------------------------------------------------------

    async def get_access_token(self, bot_config: WebhookBotConfig) -> str:
        """获取（或缓存的）access_token。"""
        cached = self._access_tokens.get(bot_config.agent_id)
        if cached and cached[1] > time.time() + 60:
            return cached[0]

        api_base = str(
            bot_config.api_base or self.wxwork_config.wxwork_api_base
        ).rstrip("/")
        params = urlencode(
            {"corpid": bot_config.corpid, "corpsecret": bot_config.corpsecret}
        )
        req = Request("GET", f"{api_base}/cgi-bin/gettoken?{params}")
        resp_data = await self.send_request(req)
        if isinstance(resp_data, dict) and resp_data.get("errcode", 0) != 0:
            raise ActionFailed(**resp_data)
        token = resp_data["access_token"]
        expires_in = resp_data.get("expires_in", 7200)
        self._access_tokens[bot_config.agent_id] = (token, time.time() + expires_in)
        return token

    @override
    async def _call_api(self, bot: Any, api: str, **data: Any) -> Any:
        if not isinstance(self.driver, HTTPClientMixin):
            raise ApiNotAvailable from None
        assert isinstance(bot, Bot)

        bot_config = bot.bot_config
        api_base = str(
            bot_config.api_base or self.wxwork_config.wxwork_api_base
        ).rstrip("/")

        # WebSocket 模式：通过 WS 发送命令
        if isinstance(bot_config, WsBotConfig):
            return await self._ws_call_api(bot, api, **data)

        # Webhook 模式：通过 REST API 发送
        assert isinstance(bot_config, WebhookBotConfig)
        access_token = await self.get_access_token(bot_config)

        if api == "send_message":
            payload = dict(data)
            url = f"{api_base}/cgi-bin/message/send?access_token={access_token}"
            req = Request("POST", url, json=payload)
            return await self.send_request(req)

        # 通用 API 透传
        method = data.pop("__method__", "POST")
        url = f"{api_base}/{api.lstrip('/')}?access_token={access_token}"
        if method == "GET":
            req = Request("GET", f"{url}&{urlencode(data)}")
        else:
            req = Request(method, url, json=data)
        return await self.send_request(req)

    async def _ws_call_api(self, bot: "Bot", api: str, **data: Any) -> Any:
        """通过 WebSocket 发送命令（长连接模式）。"""
        ws = bot._ws
        if ws is None:
            raise RuntimeError("WebSocket not connected")
        req_id = data.pop("__req_id__", str(uuid.uuid4()))
        payload = {
            "cmd": api,
            "headers": {"req_id": req_id},
            "body": data,
        }
        await ws.send_text(json.dumps(payload))
        return {"errcode": 0, "errmsg": "ok"}

    async def send_request(self, request: Request) -> Any:
        if not isinstance(self.driver, HTTPClientMixin):
            raise ApiNotAvailable from None
        try:
            response = await self.driver.request(request)
        except WxWorkAdapterException:
            raise
        except Exception as e:
            raise NetworkError("HTTP request failed") from e

        if 200 <= response.status_code < 300:
            if not response.content:
                raise ValueError("Empty response")
            if response.headers.get("Content-Type", "").find("application/json") != -1:
                result = json.loads(response.content)
                if isinstance(result, dict) and result.get("errcode", 0) != 0:
                    raise ActionFailed(**result)
                return result
            return response.content

        raise NetworkError(
            f"HTTP request received unexpected status code: {response.status_code}, "
            f"response content: {response.content!r}"
        )
