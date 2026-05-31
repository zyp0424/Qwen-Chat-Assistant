from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "default.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
