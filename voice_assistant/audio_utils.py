from __future__ import annotations

import os
import wave
from contextlib import contextmanager
from pathlib import Path

import numpy as np


@contextmanager
def silence_stderr():
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(devnull)


def read_wav_mono(path: str | Path) -> tuple[int, np.ndarray]:
    return read_wav_channel(path)


def read_wav_channel(
    path: str | Path,
    input_channel: str = "mix",
    gain: float = 1.0,
) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raise ValueError(f"Only 16-bit PCM WAV is supported, got sample width {sample_width}")

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    samples = select_mono_channel(samples, channels, input_channel)
    return sample_rate, apply_input_gain(samples, gain)


def pcm16_bytes_to_mono(
    data: bytes,
    channels: int,
    input_channel: str = "mix",
    gain: float = 1.0,
) -> np.ndarray:
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    samples = select_mono_channel(samples, channels, input_channel)
    return apply_input_gain(samples, gain)


def select_mono_channel(samples: np.ndarray, channels: int, input_channel: str = "mix") -> np.ndarray:
    if channels <= 1:
        return samples
    frames = samples.reshape(-1, channels)
    if input_channel == "left":
        return frames[:, 0]
    if input_channel == "right":
        return frames[:, min(1, channels - 1)]
    return frames.mean(axis=1)


def apply_input_gain(samples: np.ndarray, gain: float = 1.0) -> np.ndarray:
    if gain == 1.0:
        return samples
    return np.clip(samples * gain, -1.0, 1.0)


def resample_mono(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or len(samples) == 0:
        return samples.astype(np.float32, copy=False)
    target_len = max(1, int(round(len(samples) * target_rate / source_rate)))
    source_positions = np.linspace(0, len(samples) - 1, num=len(samples), dtype=np.float32)
    target_positions = np.linspace(0, len(samples) - 1, num=target_len, dtype=np.float32)
    return np.interp(target_positions, source_positions, samples).astype(np.float32)


def samples_to_pcm16(
    samples: np.ndarray,
    source_rate: int,
    target_rate: int,
    channels: int,
    mode: str = "stereo_dup",
) -> bytes:
    resampled = resample_mono(samples, source_rate, target_rate)
    clipped = np.clip(resampled, -1.0, 1.0)
    if channels == 2:
        if mode == "right_only":
            stereo = np.column_stack((np.zeros_like(clipped), clipped))
        else:
            stereo = np.column_stack((clipped, clipped))
        pcm = (stereo.reshape(-1) * 32767.0).astype(np.int16)
    else:
        pcm = (clipped * 32767.0).astype(np.int16)
    return pcm.tobytes()

