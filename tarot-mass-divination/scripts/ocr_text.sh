#!/bin/bash
# 系统 Swift + Vision OCR（macOS），图片文字识别。本机 Python 无 ocrmac，默认用此工具。
# 用法: ocr_text.sh <图片路径> [识别语言, 默认 zh-Hans]
set -euo pipefail
IMG="${1:?用法: ocr_text.sh <图片路径> [语言]}"
LANG="${2:-zh-Hans}"
SRC="$(cd "$(dirname "$0")" && pwd)/ocr_check.swift"
BIN="${HOME}/.cache/tarot-ocr/ocr_check"
if [ ! -x "$BIN" ] || [ "$SRC" -nt "$BIN" ]; then
  mkdir -p "$(dirname "$BIN")"
  swiftc "$SRC" -o "$BIN"
fi
exec "$BIN" "$IMG" "$LANG"
