#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

seconds="${1:-3}"
wav="/tmp/qwen_voice_assistant/wake_test.wav"
mkdir -p /tmp/qwen_voice_assistant

echo "Recording ${seconds}s. Say only: 鲁班猫 or 拍照助手."
.venv/bin/python voice_assistant.py record --seconds "$seconds" --out "$wav"
echo "KWS result:"
.venv/bin/python voice_assistant.py kws-file "$wav"
echo "STT result:"
.venv/bin/python voice_assistant.py stt "$wav"
rm -f "$wav"
