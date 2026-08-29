from __future__ import annotations

import queue
import struct
import threading
from typing import Callable

from northcord.utils.logger import get_logger

logger = get_logger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 2
FRAME_SIZE = 960
SILENCE_THRESHOLD = 500


class AudioProcessor:
    def __init__(self):
        self._input_queue: queue.Queue[bytes] = queue.Queue()
        self._output_queue: queue.Queue[bytes] = queue.Queue()
        self._running = False
        self._encode_thread: threading.Thread | None = None
        self._decode_thread: threading.Thread | None = None
        self._vad_threshold: float = 0.5
        self._on_audio_frame: Callable | None = None

    def start(self) -> None:
        self._running = True
        self._encode_thread = threading.Thread(target=self._encode_loop, daemon=True)
        self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._encode_thread.start()
        self._decode_thread.start()
        logger.info("Audio processor started")

    def stop(self) -> None:
        self._running = False
        if self._encode_thread:
            self._encode_thread.join(timeout=2)
        if self._decode_thread:
            self._decode_thread.join(timeout=2)
        logger.info("Audio processor stopped")

    def feed_audio(self, data: bytes) -> None:
        self._input_queue.put(data)

    def get_audio(self) -> bytes | None:
        try:
            return self._output_queue.get_nowait()
        except queue.Empty:
            return None

    def _encode_loop(self) -> None:
        while self._running:
            try:
                data = self._input_queue.get(timeout=0.1)
                frames = self._pcm_to_frames(data)
                for frame in frames:
                    encoded = self._encode_opus(frame)
                    if encoded and self._on_audio_frame:
                        self._on_audio_frame(encoded)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Encode error: %s", e)

    def _decode_loop(self) -> None:
        while self._running:
            try:
                pass
            except Exception as e:
                logger.error("Decode error: %s", e)

    def _pcm_to_frames(self, pcm_data: bytes) -> list[bytes]:
        frame_size_bytes = FRAME_SIZE * 2 * CHANNELS
        frames = []
        for i in range(0, len(pcm_data), frame_size_bytes):
            frame = pcm_data[i : i + frame_size_bytes]
            if len(frame) == frame_size_bytes:
                frames.append(frame)
        return frames

    def _encode_opus(self, pcm_frame: bytes) -> bytes | None:
        try:
            import opuslib

            encoder = opuslib.Encoder(
                sample_rate=SAMPLE_RATE,
                channels=CHANNELS,
                application=opuslib.APPLICATION_AUDIO,
            )
            return encoder.encode(pcm_frame, FRAME_SIZE)
        except ImportError:
            logger.debug("opuslib not available, returning raw PCM")
            return pcm_frame
        except Exception as e:
            logger.error("Opus encode error: %s", e)
            return None

    def detect_voice_activity(self, pcm_frame: bytes) -> bool:
        if len(pcm_frame) < 2:
            return False
        samples = struct.unpack(f"<{len(pcm_frame) // 2}h", pcm_frame)
        amplitude = sum(abs(s) for s in samples) / len(samples)
        return amplitude > SILENCE_THRESHOLD

    def set_vad_threshold(self, threshold: float) -> None:
        self._vad_threshold = max(0.0, min(1.0, threshold))

    def set_on_audio_frame(self, callback: Callable) -> None:
        self._on_audio_frame = callback
