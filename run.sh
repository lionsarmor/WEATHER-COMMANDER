#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
weather_tools="${X16_TOOLS:-$HOME/Desktop/Roddy Software/DESK COMMANDER/.tools}"
if [[ -z "${X16_TOOLS:-}" && -f .tools/READY ]]; then weather_tools="$PWD/.tools"; fi
weather_python=python3
if [[ -x .venv/bin/python ]]; then weather_python="$PWD/.venv/bin/python"; fi
weather_build=true
weather_wifi=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build) weather_build=false; shift ;;
        --wifi) weather_wifi=true; shift ;;
        *) break ;;
    esac
done
weather_emulator="$weather_tools/x16emu/x16emu"
weather_rom="$weather_tools/x16emu/rom.bin"
weather_flags=()
if "$weather_wifi"; then
    weather_emulator="${WEATHER_WIFI_EMULATOR:-$HOME/Desktop/X16-emulator-wifi-support/x16-emulator/build/x16emu}"
    weather_rom="$(dirname -- "$weather_emulator")/rom.bin"
    weather_flags=(-wifi)
fi
if [[ ! -x "$weather_emulator" || ! -f "$weather_rom" ]]; then
    echo "Emulator or ROM missing: $weather_emulator / $weather_rom" >&2
    exit 1
fi
if "$weather_build"; then
    "$weather_python" tools/build.py
fi
exec "$weather_emulator" -rom "$weather_rom" "${weather_flags[@]}" \
    -fsroot "$PWD/dist/sdcard" -startin "$PWD/dist/sdcard" \
    -prg "$PWD/dist/sdcard/WEATHER.PRG" -run -rtc -scale 2 "$@"
