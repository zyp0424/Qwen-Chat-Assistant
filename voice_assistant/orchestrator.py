from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .asr import SherpaAsr
from .audio_io import AudioRecorder
from .camera import CameraAdapter
from .intent import IntentRouter
from .qwen_runner import QwenRunner
from .streaming_tts import StreamingTtsPlayer
from .wake import SherpaKeywordWake, SttKeywordWake


class VoiceAssistant:
    def __init__(self, config: dict):
        self.config = config
        self.temp_dir = Path(config["paths"]["temp_dir"])
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.intent = IntentRouter.from_config(config)

    def transcribe_wav(self, wav_path: str | Path) -> str:
        return SherpaAsr(self.config).transcribe_wav(wav_path)

    def record_command(self, seconds: int | None = None) -> Path:
        seconds = seconds or int(self.config["audio"]["command_seconds"])
        out = self.temp_dir / "command.wav"
        out.unlink(missing_ok=True)
        return AudioRecorder(self.config).record_wav(out, seconds)

    def wait_for_wake(self, mode: str = "kws", timeout: int | None = None) -> str:
        if mode == "stt":
            return SttKeywordWake(self.config, self.temp_dir).wait(timeout=timeout)
        return SherpaKeywordWake(self.config).wait(timeout=timeout)

    def detect_wake_wav(self, wav_path: str | Path) -> str:
        return SherpaKeywordWake(self.config).detect_wav(wav_path)

    def capture_photo(self) -> Path:
        return CameraAdapter(self.config).capture()

    def ask_qwen(
        self,
        text: str,
        image_path: str | Path | None = None,
        force_photo: bool = False,
        on_sentence=None,
    ) -> str:
        intent = self.intent.analyze(text)
        uses_photo = force_photo or intent.need_photo
        if uses_photo:
            print("检测到拍照意图，正在拍照...", flush=True)
            image = self.capture_photo()
            print(f"照片已保存：{image}", flush=True)
        else:
            image = Path(image_path or self.config["paths"]["placeholder_image"])
        qwen_text = self._prepare_qwen_text(intent.qwen_text, uses_photo)
        print("正在调用 Qwen demo，请等待模型回答...", flush=True)
        runner = QwenRunner(self.config)
        if on_sentence is not None:
            return runner.ask_stream(image, qwen_text, on_sentence=on_sentence)
        return runner.ask(image, qwen_text)

    def _prepare_qwen_text(self, qwen_text: str, uses_photo: bool) -> str:
        marker = str(self.config["qwen"].get("demo_image_marker", "<image>"))
        image_prefix = str(self.config["intent"]["image_prefix"])
        should_attach_image = uses_photo or qwen_text.startswith(image_prefix)
        if should_attach_image and marker not in qwen_text:
            return f"{marker}{qwen_text}"
        return qwen_text

    def run_once_from_text(
        self,
        text: str,
        *,
        image_path: str | Path | None = None,
        force_photo: bool = False,
        speak: bool = True,
        play: bool = True,
    ) -> str:
        if speak and play:
            print("将使用流式 TTS：Qwen 每生成一句就直接写入喇叭 PCM 播放。", flush=True)
            player = StreamingTtsPlayer(self.config)
            try:
                ack_text = str(self.config["models"]["tts"].get("ack_text", "")).strip()
                if ack_text:
                    player.enqueue(ack_text)
                return self.ask_qwen(
                    text,
                    image_path=image_path,
                    force_photo=force_photo,
                    on_sentence=player.enqueue,
                )
            finally:
                player.close()
        return self.ask_qwen(text, image_path=image_path, force_photo=force_photo)

    def run_once_from_microphone(self, seconds: int | None = None, *, speak: bool = True, play: bool = True) -> str:
        command_wav = self.record_command(seconds)
        try:
            text = self.transcribe_wav(command_wav)
        finally:
            command_wav.unlink(missing_ok=True)
        if not text:
            raise RuntimeError("STT produced empty text")
        print(f"识别文本：{text}", flush=True)
        return self.run_once_from_text(text, speak=speak, play=play)

    def listen_once(
        self,
        *,
        wake_mode: str = "kws",
        wake_timeout: int | None = None,
        seconds: int | None = None,
        speak: bool = True,
        play: bool = True,
    ) -> str:
        keyword = self.wait_for_wake(mode=wake_mode, timeout=wake_timeout)
        print(f"wake={keyword}", flush=True)
        return self.run_once_from_microphone(seconds=seconds, speak=speak, play=play)

    def listen_forever(
        self,
        *,
        wake_mode: str = "kws",
        wake_timeout: int | None = None,
        seconds: int | None = None,
        speak: bool = True,
        play: bool = True,
    ) -> None:
        round_idx = 0
        while True:
            round_idx += 1
            try:
                print(f"等待唤醒词，第 {round_idx} 轮。", flush=True)
                answer = self.listen_once(
                    wake_mode=wake_mode,
                    wake_timeout=wake_timeout,
                    seconds=seconds,
                    speak=speak,
                    play=play,
                )
                print(answer, flush=True)
                print("本轮结束，继续等待唤醒词。", flush=True)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"本轮失败，继续等待唤醒词：{exc}", file=sys.stderr, flush=True)
                self.cleanup_temp()

    def cleanup_temp(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
