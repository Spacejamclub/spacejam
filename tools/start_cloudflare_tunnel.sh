#!/bin/zsh
set -euo pipefail

ROOT_DIR="/Users/space_plug/Desktop/SPACE_JAM"
export HOME="$ROOT_DIR"

exec "$ROOT_DIR/tools/cloudflared" tunnel \
  --config "$ROOT_DIR/.cloudflared/config.yml" \
  run \
  --protocol http2 \
  spacejam-miniapp
