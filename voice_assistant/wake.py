from __future__ import annotations

import subprocess
import time
from pathlib import Path

import numpy as np
import sherpa_onnx

from .audio_utils import pcm16_bytes_to_mono, read_wav_channel, silence_stderr
from .asr import SherpaAsr
from .audio_io import AudioRecorder, apply_mic_mixer_settings


class SherpaKeywordWake:
    def __init__(self, config: dict):
        apply_mic_mixer_settings(config)
        kws = config["models"]["kws"]
        audio = config["audio"]
        self.sample_rate = int(audio["sample_rate"])
        self.device = audio["mic_device"]
        self.channels = int(audio.get("channels", 1))
        self.input_channel = str(audio.get("input_channel", "mix"))
        self.input_gain = float(audio.get("wake_input_gain", audio.get("input_gain", 1.0)))
        self.suppress_stderr_warnings = bool(kws.get("suppress_stderr_warnings", True))
        if self.suppress_stderr_warnings:
            with silence_stderr():
                self.spotter = self._create_spotter(kws)
        else:
            self.spotter = self._create_spotter(kws)

    def _create_spotter(self, kws: dict):
        return sherpa_onnx.KeywordSpotter(
            tokens=kws["tokens"],
            encoder=kws["encoder"],
            decoder=kws["decoder"],
            joiner=kws["joiner"],
            keywords_file=kws["keywords_file"],
            num_threads=int(kws.get("num_threads", 2)),
            sample_rate=self.sample_rate,
            keywords_score=float(kws.get("keywords_score", 1.5)),
            keywords_threshold=float(kws.get("keywords_threshold", 0.25)),
            provider="cpu",
        )

    def wait(self, timeout: int | None = None) -> str:
        stream = self.spotter.create_stream()
        cmd = [
            "arecord",
            "-D",
            self.device,
            "-f",
            "S16_LE",
            "-r",
            str(self.sample_rate),
            "-c",
            str(self.channels),
            "-t",
            "raw",
        ]
        start = time.monotonic()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            assert proc.stdout is not None
            chunk_bytes = int(self.sample_rate * 0.1) * self.channels * 2
            while timeout is None or time.monotonic() - start < timeout:
                data = proc.stdout.read(chunk_bytes)
                if not data:
                    if proc.poll() is not None:
                        err = ""
                        if proc.stderr is not None:
                            err = proc.stderr.read().decode("utf-8", errors="ignore").strip()
                        raise RuntimeError(f"arecord exited while waiting for wake keyword: {err}")
                    continue
                samples = pcm16_bytes_to_mono(data, self.channels, self.input_channel, self.input_gain)
                stream.accept_waveform(self.sample_rate, samples)
                while self.spotter.is_ready(stream):
                    keyword = self._decode_and_get_result(stream)
                    if keyword:
                        return keyword
            raise TimeoutError("Wake keyword wait timed out")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def detect_wav(self, wav_path: str | Path) -> str:
        sample_rate, samples = read_wav_channel(wav_path, self.input_channel, self.input_gain)
        stream = self.spotter.create_stream()
        chunk = int(sample_rate * 0.1)
        for start in range(0, len(samples), chunk):
            stream.accept_waveform(sample_rate, samples[start : start + chunk])
            while self.spotter.is_ready(stream):
                keyword = self._decode_and_get_result(stream)
                if keyword:
                    return keyword
        stream.input_finished()
        while self.spotter.is_ready(stream):
            keyword = self._decode_and_get_result(stream)
            if keyword:
                return keyword
        return ""

    def _decode_and_get_result(self, stream) -> str:
        if self.suppress_stderr_warnings:
            with silence_stderr():
                self.spotter.decode_stream(stream)
                return self.spotter.get_result(stream)
        self.spotter.decode_stream(stream)
        return self.spotter.get_result(stream)


class SttKeywordWake:
    """Fallback wake detector using short STT chunks. It writes only temporary chunks."""

    def __init__(self, config: dict, temp_dir: Path):
        self.config = config
        self.temp_dir = temp_dir
        self.wake_words = ("鲁班猫", "拍照助手")
        self.chunk_seconds = int(config["audio"].get("wake_chunk_seconds", 2))
        self.recorder = AudioRecorder(config)
        self.asr = SherpaAsr(config)

    def wait(self, timeout: int | None = None) -> str:
        start = time.monotonic()
        idx = 0
        while timeout is None or time.monotonic() - start < timeout:
            idx += 1
            wav = self.temp_dir / f"wake_chunk_{idx}.wav"
            try:
                self.recorder.record_wav(wav, self.chunk_seconds)
                text = self.asr.transcribe_wav(wav)
                for wake_word in self.wake_words:
                    if wake_word in text:
                        return wake_word
            finally:
                wav.unlink(missing_ok=True)
        raise TimeoutError("Wake keyword wait timed out")
