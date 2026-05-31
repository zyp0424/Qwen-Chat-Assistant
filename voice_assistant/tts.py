from __future__ import annotations

import numpy as np
import sherpa_onnx

from .audio_utils import silence_stderr


class SherpaTts:
    def __init__(self, config: dict):
        tts_cfg = config["models"]["tts"]
        model_type = str(tts_cfg.get("type", "vits")).lower()
        if model_type == "matcha":
            acoustic = tts_cfg.get("acoustic_model") or tts_cfg.get("model")
            model_kwargs = dict(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=acoustic,
                    vocoder=tts_cfg["vocoder"],
                    lexicon=tts_cfg["lexicon"],
                    tokens=tts_cfg["tokens"],
                    data_dir=tts_cfg["data_dir"],
                    noise_scale=float(tts_cfg.get("noise_scale", 1.0)),
                    length_scale=float(tts_cfg.get("length_scale", 1.0)),
                )
            )
        elif model_type == "vits":
            model_kwargs = dict(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=tts_cfg["model"],
                    lexicon=tts_cfg["lexicon"],
                    tokens=tts_cfg["tokens"],
                    data_dir=tts_cfg["data_dir"],
                    noise_scale=float(tts_cfg.get("noise_scale", 0.667)),
                    noise_scale_w=float(tts_cfg.get("noise_scale_w", 0.8)),
                    length_scale=float(tts_cfg.get("length_scale", 1.0)),
                )
            )
        else:
            raise ValueError(f"Unsupported TTS model type: {model_type}")

        model = sherpa_onnx.OfflineTtsModelConfig(
            **model_kwargs,
            num_threads=int(tts_cfg.get("num_threads", 2)),
            provider="cpu",
        )
        self.sid = int(tts_cfg.get("sid", 0))
        self.speed = float(tts_cfg.get("speed", 1.0))
        self.suppress_stderr_warnings = bool(tts_cfg.get("suppress_stderr_warnings", True))
        if self.suppress_stderr_warnings:
            with silence_stderr():
                self.tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=model))
        else:
            self.tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=model))

    def synthesize_samples(self, text: str) -> tuple[int, np.ndarray]:
        if self.suppress_stderr_warnings:
            with silence_stderr():
                audio = self.tts.generate(text, sid=self.sid, speed=self.speed)
        else:
            audio = self.tts.generate(text, sid=self.sid, speed=self.speed)
        return int(audio.sample_rate), audio.samples
