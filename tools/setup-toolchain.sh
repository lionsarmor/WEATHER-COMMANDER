#!/usr/bin/env bash
# Install the pinned build tools locally. Requires Java 21+, curl, unzip, make, cc.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
weather_tools="$PWD/.tools"
for weather_command in curl unzip make cc java sha256sum; do
    command -v "$weather_command" >/dev/null || { echo "Install $weather_command first (Java must be 21 or newer)." >&2; exit 1; }
done
mkdir -p "$weather_tools"/{bin,downloads,prog8,jre/bin,src}
weather_download() {
    local url="$1" destination="$2" digest="$3"
    if [[ ! -f "$destination" ]] || ! echo "$digest  $destination" | sha256sum --check --status; then
        curl --fail --location --retry 3 --show-error "$url" --output "$destination.part"
        echo "$digest  $destination.part" | sha256sum --check --status
        mv -- "$destination.part" "$destination"
    fi
}
weather_download 'https://github.com/irmen/prog8/releases/download/v12.3.2/prog8c-12.3.2-all.jar' \
    "$weather_tools/prog8/prog8c-12.3.2-all.jar" \
    f57afb6e09288b97f552414dba20a80bff8d1bf9f05d991258345cb508028ec7
weather_download 'https://sourceforge.net/projects/tass64/files/source/64tass-1.60.3243-src.zip/download' \
    "$weather_tools/downloads/64tass-1.60.3243-src.zip" \
    9d83be3d23a2c55e085b7c7a7856c2f96080447ea120a6a8c21a217ed76427f0
unzip -q -o "$weather_tools/downloads/64tass-1.60.3243-src.zip" -d "$weather_tools/src"
make -C "$weather_tools/src/64tass-1.60.3243-src" -j2
cp "$weather_tools/src/64tass-1.60.3243-src/64tass" "$weather_tools/bin/64tass"
if [[ ! -e "$weather_tools/jre/bin/java" ]]; then ln -s "$(command -v java)" "$weather_tools/jre/bin/java"; fi
"$weather_tools/jre/bin/java" -jar "$weather_tools/prog8/prog8c-12.3.2-all.jar" -version
"$weather_tools/bin/64tass" --version
touch "$weather_tools/READY"
echo 'Build tools ready. Run ./buildweather (add --check for the full compiled tests).'
echo 'Emulator is separate: install r49 and rom.bin under .tools/x16emu to use ./run.sh.'
