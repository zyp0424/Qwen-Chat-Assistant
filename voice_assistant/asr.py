from __future__ import annotations

from pathlib import Path

import sherpa_onnx

from .audio_utils import read_wav_channel, silence_stderr


class SherpaAsr:
    def __init__(self, config: dict):
        model = config["models"]["asr"]
        audio = config["audio"]
        self.input_channel = str(audio.get("input_channel", "mix"))
        self.input_gain = float(audio.get("asr_input_gain", audio.get("input_gain", 1.0)))
        self.suppress_stderr_warnings = bool(model.get("suppress_stderr_warnings", True))
        if self.suppress_stderr_warnings:
            with silence_stderr():
                self.recognizer = self._create_recognizer(model)
        else:
            self.recognizer = self._create_recognizer(model)

    def transcribe_wav(self, wav_path: str | Path) -> str:
        sample_rate, samples = read_wav_channel(wav_path, self.input_channel, self.input_gain)
        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        if self.suppress_stderr_warnings:
            with silence_stderr():
                self.recognizer.decode_stream(stream)
                return stream.result.text.strip()
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()

    @staticmethod
    def _create_recognizer(model: dict):
        return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=model["encoder"],
            decoder=model["decoder"],
            joiner=model["joiner"],
            tokens=model["tokens"],
            num_threads=int(model.get("num_threads", 2)),
            provider="cpu",
        )
