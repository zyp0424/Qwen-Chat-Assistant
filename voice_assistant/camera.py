from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


class CameraAdapter:
    def __init__(self, config: dict):
        paths = config["paths"]
        self.capture_script = Path(paths["capture_script"])
        self.temp_dir = Path(paths["temp_dir"])
        self.photo_dir = Path(paths["photo_dir"])

    def capture(self) -> Path:
        work_dir = self.temp_dir / "capture_work"
        work_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cmd = [
            str(self.capture_script),
            "--out-dir",
            str(work_dir),
            "--prefix",
            "voice",
            "--timestamp",
            timestamp,
        ]
        proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
        parsed = self._parse_key_values(proc.stdout)
        jpg = Path(parsed["jpg"])
        raw = Path(parsed.get("raw", ""))
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        final_jpg = self.photo_dir / jpg.name
        shutil.move(str(jpg), str(final_jpg))
        if raw:
            raw.unlink(missing_ok=True)
        return final_jpg

    @staticmethod
    def _parse_key_values(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        if "jpg" not in result:
            raise RuntimeError(f"capture script did not report jpg path: {text}")
        return result
