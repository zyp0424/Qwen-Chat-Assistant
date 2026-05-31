#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

mode="${1:-kws}"
seconds="${2:-6}"

echo "Waiting for wake word with mode=${mode}. Say: 鲁班猫 or 拍照助手."
.venv/bin/python voice_assistant.py listen --wake-mode "$mode" --seconds "$seconds"
