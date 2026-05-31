from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .audio_utils import samples_to_pcm16


class AudioRecorder:
    def __init__(self, config: dict):
        apply_mic_mixer_settings(config)
        audio = config["audio"]
        self.device = audio["mic_device"]
        self.sample_rate = int(audio["sample_rate"])
        self.channels = int(audio["channels"])

    def record_wav(self, out_path: str | Path, seconds: int) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
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
            "-d",
            str(seconds),
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True)
        except BaseException:
            out.unlink(missing_ok=True)
            raise
        return out


def apply_mic_mixer_settings(config: dict) -> None:
    audio = config["audio"]
    card = audio.get("mixer_card")
    gain = audio.get("capture_channel_gain")
    if card is None or gain is None:
        return
    for control in ("Left Channel", "Right Channel"):
        subprocess.run(
            ["amixer", "-c", str(card), "sset", control, str(gain)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class PcmSpeakerStream:
    def __init__(self, config: dict):
        audio = config["audio"]
        self.device = audio["speaker_device"]
        self.channels = int(audio.get("playback_channels", 2))
        self.sample_rate = int(audio.get("playback_sample_rate", 44100))
        self.mode = str(audio.get("playback_mode", "stereo_dup"))
        self.proc: subprocess.Popen | None = None

    def write_samples(self, sample_rate: int, samples: np.ndarray) -> None:
        if len(samples) == 0:
            return
        if self.proc is None:
            self._start()
        assert self.proc is not None and self.proc.stdin is not None
        pcm = samples_to_pcm16(
            samples,
            source_rate=sample_rate,
            target_rate=self.sample_rate,
            channels=self.channels,
            mode=self.mode,
        )
        self.proc.stdin.write(pcm)
        self.proc.stdin.flush()

    def close(self) -> None:
        if self.proc is None:
            return
        proc = self.proc
        self.proc = None
        if proc.stdin is not None:
            proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if proc.returncode not in (0, None):
            raise subprocess.CalledProcessError(proc.returncode, proc.args)

    def _start(self) -> None:
        cmd = [
            "aplay",
            "-q",
            "-D",
            self.device,
            "-t",
            "raw",
            "-f",
            "S16_LE",
            "-r",
            str(self.sample_rate),
            "-c",
            str(self.channels),
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
