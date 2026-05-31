#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

text="${1:-你好，我是本地语音助手。}"

echo "Streaming raw PCM through configured external speaker module..."
.venv/bin/python voice_assistant.py tts-stream "$text"
