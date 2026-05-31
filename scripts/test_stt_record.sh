#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

seconds="${1:-5}"
wav="/tmp/qwen_voice_assistant/test_stt.wav"
mkdir -p /tmp/qwen_voice_assistant

echo "Recording ${seconds}s to ${wav}. Speak Chinese after recording starts."
.venv/bin/python voice_assistant.py record --seconds "$seconds" --out "$wav"
echo "Transcription:"
.venv/bin/python voice_assistant.py stt "$wav"
rm -f "$wav"
