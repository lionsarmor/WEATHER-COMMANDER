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
weather_bridge_pid=""
cleanup_weather_bridge() {
    if [[ -n "$weather_bridge_pid" ]]; then
        kill "$weather_bridge_pid" 2>/dev/null || true
        wait "$weather_bridge_pid" 2>/dev/null || true
    fi
}
trap cleanup_weather_bridge EXIT
if [[ "${WEATHER_BRIDGE:-1}" != 0 ]]; then
    "$weather_python" -m backend.server --bind "${WEATHER_BIND:-127.0.0.1}" \
        --port "${WEATHER_PORT:-8767}" --output "$PWD/dist/sdcard" > build/bridge.log 2>&1 &
    weather_bridge_pid=$!
    # Give a cold fetch a short head start. The application handles unavailable
    # or expired data and automatically picks up the bridge's next snapshot.
    for weather_wait in {1..20}; do
        if [[ -f dist/sdcard/WCDATA.BIN ]]; then break; fi
        if ! kill -0 "$weather_bridge_pid" 2>/dev/null; then break; fi
        sleep 0.25
    done
fi
"$weather_tools/x16emu/x16emu" -rom "$weather_tools/x16emu/rom.bin" \
    -fsroot "$PWD/dist/sdcard" -startin "$PWD/dist/sdcard" \
    -prg "$PWD/dist/sdcard/WEATHER.PRG" -run -rtc -scale 2 "$@"
