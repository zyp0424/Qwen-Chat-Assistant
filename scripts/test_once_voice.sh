#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

seconds="${1:-6}"
echo "Recording one Chinese voice command for ${seconds}s, then running the full pipeline."
.venv/bin/python voice_assistant.py once --seconds "$seconds"
