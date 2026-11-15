#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != "Darwin" ]; then
  echo "Run this builder on macOS. No Windows cross-compilation is supported."
  exit 1
fi
python3 -m venv .venv-macos
.venv-macos/bin/python -m pip install --upgrade pip
.venv-macos/bin/python -m pip install . pyinstaller pillow
.venv-macos/bin/python tools/build_macos.py
