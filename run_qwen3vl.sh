#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

chmod +x ./demo ./imgenc

export LD_LIBRARY_PATH=".:${LD_LIBRARY_PATH:-}"
export RKLLM_LOG_LEVEL=1

if ! ulimit -HSn 10240 2>/dev/null; then
  ulimit -Sn 10240 2>/dev/null || true
fi

IMAGE_DIR="/home/cat/图片"
LATEST_IMAGE="$(
  find "$IMAGE_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) -printf '%T@ %p\n' |
    sort -nr |
    head -n 1 |
    cut -d' ' -f2-
)"

if [[ -z "$LATEST_IMAGE" ]]; then
  echo "No JPG/JPEG image found in $IMAGE_DIR" >&2
  exit 1
fi

echo "Using image: $LATEST_IMAGE"

exec ./demo "$LATEST_IMAGE" \
  ./qwen3-vl-2b_vision_rk3588.rknn \
  ./qwen3-vl-2b-instruct_w8a8_rk3588.rkllm \
  2048 4096 3 \
  "<|vision_start|>" "<|vision_end|>" "<|image_pad|>"
