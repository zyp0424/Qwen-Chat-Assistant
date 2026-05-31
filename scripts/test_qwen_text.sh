#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

text="${1:-请简单描述这张图片。}"
image="${2:-demo.jpg}"

echo "Asking Qwen with image=$image"
.venv/bin/python voice_assistant.py ask "$text" --image "$image" --no-speak --no-play
