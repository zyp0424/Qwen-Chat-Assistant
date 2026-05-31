#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

mode="${1:-kws}"
seconds="${2:-6}"

echo "Persistent mode with wake mode=${mode}. Say: 鲁班猫 or 拍照助手. Press Ctrl+C to exit."
.venv/bin/python voice_assistant.py listen-forever --wake-mode "$mode" --seconds "$seconds"
