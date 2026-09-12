#!/usr/bin/env bash
# Run on the weather computer while a physical X16 uses its Wi-Fi modem.
set -euo pipefail
cd -- "$(dirname -- "$0")"
weather_python=python3
if [[ -x .venv/bin/python ]]; then weather_python="$PWD/.venv/bin/python"; fi
weather_output=.
if [[ -d dist/sdcard ]]; then weather_output=dist/sdcard; fi
exec "$weather_python" -m backend.server --bind 0.0.0.0 --port "${WEATHER_PORT:-8767}" --output "$weather_output" "$@"
