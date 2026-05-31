from __future__ import annotations

import queue
import threading
from typing import Optional

from .audio_io import PcmSpeakerStream
from .text_clean import sanitize_tts_text
from .tts import SherpaTts


class StreamingTtsPlayer:
    def __init__(self, config: dict):
        self.config = config
        self.max_chars = int(config["models"]["tts"].get("stream_max_speak_chars", 220))
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="streaming-tts-player", daemon=True)
        self._thread.start()

    def enqueue(self, text: str) -> None:
        if self._error is not None:
            raise RuntimeError("streaming TTS worker failed") from self._error
        cleaned = sanitize_tts_text(text, max_chars=self.max_chars, fallback=None)
        if cleaned:
            self._queue.put(cleaned)

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join()
        if self._error is not None:
            raise RuntimeError("streaming TTS worker failed") from self._error

    def _run(self) -> None:
        speaker = PcmSpeakerStream(self.config)
        tts: SherpaTts | None = None
        try:
            while True:
                text = self._queue.get()
                if text is None:
                    break
                if tts is None:
                    tts = SherpaTts(self.config)
                sample_rate, samples = tts.synthesize_samples(text)
                speaker.write_samples(sample_rate, samples)
        except BaseException as exc:
            self._error = exc
        finally:
            try:
                speaker.close()
            except BaseException as exc:
                if self._error is None:
                    self._error = exc
