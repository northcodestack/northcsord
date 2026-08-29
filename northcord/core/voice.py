from __future__ import annotations

import asyncio
import json
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Any, Callable

from northcord.utils.logger import get_logger

logger = get_logger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 2
FRAME_SIZE = 960
OPUS_FRAME_DURATION = 20


class VoiceClient:
    def __init__(self, token: str, guild_id: str, channel_id: str):
        self.token = token
        self.guild_id = guild_id
        self.channel_id = channel_id
        self._endpoint: str | None = None
        self._voice_token: str | None = None
        self._session_id: str | None = None
        self._ws: Any = None
        self._udp_socket: socket.socket | None = None
        self._ssrc: int = 0
        self._server_ip: str | None = None
        self._server_port: int = 0
        self._secret_key: list[int] = []
        self._sequence: int = 0
        self._timestamp: int = 0
        self._running = False
        self._playing = False
        self._paused = False
        self._looping = False
        self._volume: int = 100
        self._on_speaking: Callable[[bool], None] | None = None
        self._event_handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error("Voice event handler error %s: %s", event, e)

    async def connect(self) -> bool:
        if self._running:
            logger.warning("Already connected to voice")
            return False

        logger.info("Connecting to voice channel %s in guild %s", self.channel_id, self.guild_id)
        self._running = True
        self._connect_websocket()
        return True

    def _connect_websocket(self) -> None:
        if not self._endpoint:
            logger.error("No voice endpoint available")
            return

        ws_url = f"wss://{self._endpoint}?v=4"

        def run_ws():
            self._ws = websocket.WebSocket()
            try:
                self._ws.connect(ws_url)
                self._ws.settimeout(10)
                self._voice_identify()
                self._voice_ws_loop()
            except Exception as e:
                logger.error("Voice WebSocket error: %s", e)
                self._running = False

        thread = threading.Thread(target=run_ws, daemon=True)
        thread.start()

    def _voice_identify(self) -> None:
        if not self._ws or not self._session_id:
            return
        payload = {
            "op": 0,
            "d": {
                "server_id": self.guild_id,
                "user_id": "0",
                "session_id": self._session_id,
                "token": self._voice_token,
            },
        }
        self._ws.send(json.dumps(payload))
        logger.info("Voice identify sent")

    def _voice_ws_loop(self) -> None:
        while self._running and self._ws:
            try:
                message = self._ws.recv()
                if not message:
                    break
                data = json.loads(message)
                self._handle_voice_ws(data)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                if self._running:
                    logger.error("Voice WS loop error: %s", e)
                break

    def _handle_voice_ws(self, data: dict[str, Any]) -> None:
        op = data.get("op")
        d = data.get("d", {})

        if op == 2:
            self._ssrc = d.get("ssrc", 0)
            self._server_ip = d.get("ip")
            self._server_port = d.get("port")
            logger.info("Voice ready: ssrc=%d, %s:%d", self._ssrc, self._server_ip, self._server_port)
            self._connect_udp()

        elif op == 4:
            self._secret_key = d.get("secret_key", [])
            logger.info("Voice session description received (key length: %d)", len(self._secret_key))
            self._emit("ready")

        elif op == 5:
            speaking = d.get("speaking", 0)
            user_id = d.get("user_id")
            logger.debug("Speaking update: user=%s speaking=%d", user_id, speaking)

        elif op == 8:
            logger.info("Voice heartbeat ACK")
        elif op == 9:
            logger.info("Voice spoke")

        elif op == 3:
            self._connect_websocket()

    def _connect_udp(self) -> None:
        if not self._server_ip or not self._server_port:
            logger.error("No server info for UDP connection")
            return

        try:
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_socket.settimeout(5.0)

            discovery_packet = struct.pack(">HHIH", 0x1, 0x46, self._ssrc, 0)
            self._udp_socket.sendto(discovery_packet, (self._server_ip, self._server_port))

            data, _ = self._udp_socket.recvfrom(70)
            our_ip = socket.inet_ntoa(data[8:12])
            our_port = struct.unpack(">H", data[24:26])[0]

            self._select_protocol(our_ip, our_port)
            logger.info("UDP connected: %s:%d", our_ip, our_port)

        except socket.timeout:
            logger.error("UDP discovery timed out")
        except Exception as e:
            logger.error("UDP connection failed: %s", e)

    def _select_protocol(self, ip: str, port: int) -> None:
        if not self._ws:
            return
        payload = {
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": ip,
                    "port": port,
                    "mode": "aead_aes256_gcm_rtpsize",
                },
            },
        }
        self._ws.send(json.dumps(payload))

    def _encode_audio(self, audio_data: bytes) -> bytes:
        try:
            import opuslib

            encoder = opuslib.Encoder(
                sample_rate=SAMPLE_RATE,
                channels=CHANNELS,
                application=opuslib.APPLICATION_AUDIO,
            )
            return encoder.encode(audio_data, FRAME_SIZE)
        except ImportError:
            logger.debug("opuslib not available, returning raw PCM")
            return audio_data
        except Exception as e:
            logger.error("Opus encode error: %s", e)
            return audio_data

    def _encrypt_packet(self, header: bytes, audio_data: bytes) -> bytes:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            key = bytes(self._secret_key)
            nonce = header[:12]
            aesgcm = AESGCM(key)
            return header + aesgcm.encrypt(nonce, audio_data, None)
        except ImportError:
            logger.error("cryptography not available for packet encryption")
            return header + audio_data
        except Exception as e:
            logger.error("Encrypt error: %s", e)
            return header + audio_data

    def _build_rtp_header(self) -> bytes:
        header = bytearray(12)
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into(">H", header, 2, self._sequence)
        struct.pack_into(">I", header, 4, self._timestamp)
        struct.pack_into(">I", header, 8, self._ssrc)
        return bytes(header)

    def _send_voice_packet(self, audio_data: bytes) -> None:
        if not self._udp_socket:
            return
        try:
            header = self._build_rtp_header()
            encrypted = self._encrypt_packet(header, audio_data)
            self._udp_socket.sendto(encrypted, (self._server_ip, self._server_port))
            self._sequence = (self._sequence + 1) % 65536
            self._timestamp += FRAME_SIZE
        except Exception as e:
            logger.error("Failed to send voice packet: %s", e)

    async def play(self, file_path: str, volume: int = 100, loop: bool = False) -> None:
        if self._playing:
            logger.warning("Already playing audio")
            return

        path = Path(file_path)
        if not path.exists():
            logger.error("Audio file not found: %s", file_path)
            return

        self._volume = max(0, min(200, volume))
        self._looping = loop
        self._playing = True
        self._paused = False

        self._set_speaking(True)

        try:
            import miniaudio

            logger.info("Playing audio: %s (volume=%d, loop=%s)", file_path, self._volume, loop)
            self._stream_audio(path)
        except ImportError:
            logger.warning("miniaudio not available, playing PCM")
            self._stream_pcm(path)
        except Exception as e:
            logger.error("Playback error: %s", e)
            self._playing = False
            self._set_speaking(False)

    def _stream_audio(self, path: Path) -> None:
        try:
            import miniaudio

            stream = miniaudio.stream_file(str(path))
            for pcm_frame in stream:
                if not self._playing or self._paused:
                    while self._paused and self._playing:
                        time.sleep(0.1)
                    if not self._playing:
                        break

                adjusted = self._adjust_volume(pcm_frame)
                encoded = self._encode_audio(adjusted)
                if encoded:
                    self._send_voice_packet(encoded)
                time.sleep(OPUS_FRAME_DURATION / 1000.0)
        except Exception as e:
            logger.error("Stream error: %s", e)

    def _stream_pcm(self, path: Path) -> None:
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(FRAME_SIZE * CHANNELS * 2)
                    if not chunk:
                        break
                    if not self._playing:
                        break
                    while self._paused and self._playing:
                        time.sleep(0.1)

                    adjusted = self._adjust_volume(chunk)
                    encoded = self._encode_audio(adjusted)
                    if encoded:
                        self._send_voice_packet(encoded)
                    time.sleep(OPUS_FRAME_DURATION / 1000.0)
        except Exception as e:
            logger.error("PCM stream error: %s", e)

    def _adjust_volume(self, data: bytes) -> bytes:
        if self._volume == 100:
            return data

        try:
            factor = self._volume / 100.0
            samples = bytearray(data)
            for i in range(0, len(samples), 2):
                if i + 1 < len(samples):
                    sample = struct.unpack_from("<h", samples, i)[0]
                    adjusted = max(-32768, min(32767, int(sample * factor)))
                    struct.pack_into("<h", samples, i, adjusted)
            return bytes(samples)
        except Exception:
            return data

    def _set_speaking(self, speaking: bool) -> None:
        if not self._ws:
            return
        payload = {
            "op": 5,
            "d": {
                "speaking": 1 if speaking else 0,
                "delay": 0,
                "ssrc": self._ssrc,
            },
        }
        self._ws.send(json.dumps(payload))

    async def stop(self) -> None:
        self._playing = False
        self._paused = False
        self._set_speaking(False)
        logger.info("Playback stopped")

    async def pause(self) -> None:
        if self._playing and not self._paused:
            self._paused = True
            logger.info("Playback paused")

    async def resume(self) -> None:
        if self._playing and self._paused:
            self._paused = False
            logger.info("Playback resumed")

    async def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(200, volume))
        logger.info("Volume set to %d%%", self._volume)

    async def set_loop(self, loop: bool) -> None:
        self._looping = loop
        logger.info("Loop %s", "enabled" if loop else "disabled")

    def set_on_speaking(self, callback: Callable[[bool], None]) -> None:
        self._on_speaking = callback

    async def disconnect(self) -> None:
        self._running = False
        self._playing = False
        self._paused = False

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
            self._udp_socket = None

        self._endpoint = None
        self._voice_token = None
        self._session_id = None
        self._secret_key = []
        logger.info("Voice client disconnected")

    def update_server(self, endpoint: str, token: str, session_id: str) -> None:
        self._endpoint = endpoint
        self._voice_token = token
        self._session_id = session_id

    @property
    def is_connected(self) -> bool:
        return self._running and self._ws is not None

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def volume(self) -> int:
        return self._volume


import websocket
