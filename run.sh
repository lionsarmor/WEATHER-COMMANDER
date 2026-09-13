#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
weather_tools="${X16_TOOLS:-$HOME/Desktop/Roddy Software/DESK COMMANDER/.tools}"
if [[ -z "${X16_TOOLS:-}" && -f .tools/READY ]]; then weather_tools="$PWD/.tools"; fi
weather_python=python3
if [[ -x .venv/bin/python ]]; then weather_python="$PWD/.venv/bin/python"; fi
if [[ "${1:-}" != "--no-build" ]]; then
    "$weather_python" tools/build.py
else
    shift
fi
"$weather_tools/x16emu/x16emu" -rom "$weather_tools/x16emu/rom.bin" \
    -fsroot "$PWD/dist/sdcard" -startin "$PWD/dist/sdcard" \
    -prg "$PWD/dist/sdcard/WEATHER.PRG" -run -rtc -scale 2 "$@"
