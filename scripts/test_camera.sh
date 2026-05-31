#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "Capturing one photo through CameraAdapter..."
.venv/bin/python voice_assistant.py camera
echo "Latest photos:"
find /home/cat/图片 -maxdepth 1 -type f -iname '*.jpg' -printf '%T@ %p\n' | sort -nr | head -5 | cut -d' ' -f2-
