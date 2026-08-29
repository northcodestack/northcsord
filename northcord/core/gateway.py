from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable

import websocket

from northcord.utils.logger import get_logger

logger = get_logger(__name__)

GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
MAX_RECONNECT_DELAY = 30.0
BASE_RECONNECT_DELAY = 1.0


class GatewayClient:
    def __init__(self, token: str, on_event: Callable[[str, dict[str, Any]], None] | None = None):
        self.token = token
        self.on_event = on_event
        self.ws: websocket.WebSocketApp | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: asyncio.Task | None = None
        self._running = False
        self._sequence: int | None = None
        self._session_id: str | None = None
        self._heartbeat_interval: float = 41.25
        self._last_heartbeat: float = 0.0
        self._heartbeat_ack: bool = True
        self._reconnect_attempts = 0
        self._resume_url: str | None = None
        self._user: dict[str, Any] | None = None
        self._guilds: dict[str, dict[str, Any]] = {}

    async def connect(self) -> bool:
        if self._running:
            logger.warning("Gateway already connected")
            return True

        self._running = True
        self._loop = asyncio.get_running_loop()
        self._reconnect_attempts = 0
        self._start_ws()
        return True

    def _start_ws(self) -> None:
        def run_ws():
            self.ws = websocket.WebSocketApp(
                self._resume_url or GATEWAY_URL,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self.ws.run_forever(ping_interval=30, ping_timeout=10, reconnect=0)

        thread = threading.Thread(target=run_ws, daemon=True)
        thread.start()

    def _schedule_async(self, coro):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        logger.info("Gateway WebSocket connected")
        self._reconnect_attempts = 0

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse gateway message: %s", e)
            return

        op = data.get("op")
        seq = data.get("s")
        if seq is not None:
            self._sequence = seq

        event_type = data.get("t")
        event_data = data.get("d")

        if op == 10:
            self._handle_hello(event_data)
        elif op == 11:
            self._heartbeat_ack = True
            self._last_heartbeat = time.time()
        elif op == 9:
            logger.warning("Invalid session, re-identifying")
            self._send_identify()
        elif op == 7:
            logger.info("Gateway requested reconnect")
            self._schedule_reconnect()
        elif op == 0 and event_type:
            self._handle_event(event_type, event_data)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("Gateway WebSocket error: %s", error)

    def _on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        logger.info("Gateway WebSocket closed: %s %s", close_status_code, close_msg)
        if self._running:
            self._schedule_reconnect()

    def _handle_hello(self, data: dict[str, Any]) -> None:
        self._heartbeat_interval = data.get("heartbeat_interval", 41250) / 1000.0
        logger.info("Gateway hello received, heartbeat interval: %.2fs", self._heartbeat_interval)

        if self._session_id and self._sequence:
            self._send_resume()
        else:
            self._send_identify()

        self._start_heartbeat()

    def _send_identify(self) -> None:
        if not self.ws:
            return
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "os": "windows",
                    "browser": "northcord",
                    "device": "northcord",
                },
                "compress": False,
                "large_threshold": 250,
                "intents": 513,
                "presence": {
                    "status": "online",
                    "afk": False,
                    "since": 0,
                    "activities": [],
                },
            },
        }
        self.ws.send(json.dumps(payload))
        logger.info("Gateway identify sent")

    def _send_resume(self) -> None:
        if not self.ws:
            return
        payload = {
            "op": 6,
            "d": {
                "token": self.token,
                "session_id": self._session_id,
                "seq": self._sequence,
            },
        }
        self.ws.send(json.dumps(payload))
        logger.info("Gateway resume sent (session: %s, seq: %s)", self._session_id, self._sequence)

    def _start_heartbeat(self) -> None:
        def heartbeat_loop():
            while self._running and self.ws and self.ws.keep_running:
                now = time.time()
                if now - self._last_heartbeat >= self._heartbeat_interval:
                    if not self._heartbeat_ack:
                        logger.warning("Heartbeat ACK not received, reconnecting")
                        self._schedule_reconnect()
                        break
                    payload = {
                        "op": 1,
                        "d": self._sequence,
                    }
                    try:
                        self.ws.send(json.dumps(payload))
                        self._heartbeat_ack = False
                        self._last_heartbeat = now
                    except Exception as e:
                        logger.error("Heartbeat failed: %s", e)
                        break
                time.sleep(1)

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

    def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        handler_name = f"_handle_{event_type.lower()}"
        handler = getattr(self, handler_name, None)
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error("Error handling %s: %s", event_type, e)

        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception as e:
                logger.error("Error in on_event callback for %s: %s", event_type, e)

    def _handle_ready(self, data: dict[str, Any]) -> None:
        self._session_id = data.get("session_id")
        self._user = data.get("user")
        self._resume_url = data.get("resume_gateway_url")
        logger.info("Gateway ready - logged in as %s (session: %s)",
                     self._user.get("username", "unknown") if self._user else "unknown",
                     self._session_id)

    def _handle_message_create(self, data: dict[str, Any]) -> None:
        pass

    def _handle_message_update(self, data: dict[str, Any]) -> None:
        pass

    def _handle_message_delete(self, data: dict[str, Any]) -> None:
        pass

    def _handle_guild_create(self, data: dict[str, Any]) -> None:
        guild_id = data.get("id")
        if guild_id:
            self._guilds[guild_id] = data
            logger.info("Guild loaded: %s (%s)", data.get("name", "unknown"), guild_id)

    def _handle_guild_update(self, data: dict[str, Any]) -> None:
        guild_id = data.get("id")
        if guild_id and guild_id in self._guilds:
            self._guilds[guild_id].update(data)

    def _handle_guild_delete(self, data: dict[str, Any]) -> None:
        guild_id = data.get("id")
        if guild_id and guild_id in self._guilds:
            del self._guilds[guild_id]

    def _handle_channel_create(self, data: dict[str, Any]) -> None:
        pass

    def _handle_channel_update(self, data: dict[str, Any]) -> None:
        pass

    def _handle_channel_delete(self, data: dict[str, Any]) -> None:
        pass

    def _handle_voice_state_update(self, data: dict[str, Any]) -> None:
        pass

    def _handle_voice_server_update(self, data: dict[str, Any]) -> None:
        pass

    def _handle_typing_start(self, data: dict[str, Any]) -> None:
        pass

    def _handle_presence_update(self, data: dict[str, Any]) -> None:
        pass

    def _schedule_reconnect(self) -> None:
        delay = min(BASE_RECONNECT_DELAY * (2 ** self._reconnect_attempts), MAX_RECONNECT_DELAY)
        self._reconnect_attempts += 1
        logger.info("Reconnecting in %.2fs (attempt %d)", delay, self._reconnect_attempts)

        def reconnect():
            time.sleep(delay)
            if self._running:
                self._start_ws()

        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()

    async def disconnect(self) -> None:
        self._running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        self._session_id = None
        self._sequence = None
        logger.info("Gateway disconnected")

    async def send(self, op: int, data: dict[str, Any]) -> None:
        if not self.ws:
            logger.warning("Cannot send, gateway not connected")
            return
        payload = {"op": op, "d": data}
        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            logger.error("Failed to send op %d: %s", op, e)

    async def identify(self) -> None:
        self._send_identify()

    async def update_voice_state(
        self,
        guild_id: str,
        channel_id: str | None,
        mute: bool = False,
        deaf: bool = False,
    ) -> None:
        await self.send(4, {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "self_mute": mute,
            "self_deaf": deaf,
        })

    async def update_presence(self, status: str, activity: dict[str, Any] | None = None) -> None:
        await self.send(3, {
            "since": 0,
            "activities": [activity] if activity else [],
            "status": status,
            "afk": False,
        })

    async def request_guild_members(self, guild_id: str, query: str = "", limit: int = 0) -> None:
        await self.send(8, {
            "guild_id": guild_id,
            "query": query,
            "limit": limit,
        })

    @property
    def is_connected(self) -> bool:
        return bool(self.ws and self.ws.keep_running and self._running)

    @property
    def user(self) -> dict[str, Any] | None:
        return self._user

    @property
    def guilds(self) -> dict[str, dict[str, Any]]:
        return dict(self._guilds)


import threading
