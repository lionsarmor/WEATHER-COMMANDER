#!/usr/bin/env python3
"""Create reproducible, folder-based releases without personal runtime data."""
import hashlib
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from build import MODULES

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = ['WEATHER.PRG'] + [name + '.BIN' for name in MODULES.values()]
RUNTIME_FILES += ['WC' + name + '.BIN' for name in (
    'TILES', 'MAP', 'FONT', 'PAL', 'NAT', 'REG', 'RAD', 'BLK',
    'POINTER', 'HART', 'PH', 'RDEMO', 'RDPH')]
RUNTIME_FILES += [f'WCSC{i:02}.BIN' for i in range(28)]


def write_archive(destination, entries):
    # Read every required file before touching a previous good distribution.
    contents = {}
    for name, source in entries.items():
        contents[name] = (source.read_bytes(), bool(source.stat().st_mode & 0o111)) if isinstance(source, Path) else (source, False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with ZipFile(temporary_path, 'w', ZIP_DEFLATED) as archive:
            for name, (data, executable) in sorted(contents.items()):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100755 if executable else 0o100644) << 16
                info.compress_type = ZIP_DEFLATED
                archive.writestr(info, data)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    version = (ROOT / 'VERSION').read_text().strip()
    x16 = {'WEATHER/' + name: ROOT / 'dist/sdcard' / name for name in RUNTIME_FILES}
    x16['WEATHER/START-HERE.TXT'] = f'''WEATHER COMMANDER {version} - COMMANDER X16

Copy the entire WEATHER folder to your X16 SD card (device 8).
Keep every PRG and BIN together. Requires 512 KB RAM; tested on ROM r49.

At the BASIC prompt:
  DOS "CD:WEATHER"
  LOAD "WEATHER.PRG",8
  RUN

The app starts with clearly labeled demo data if no live feed is available.
Mouse selects controls. F5 opens Settings. Esc exits (or goes back in setup).

LIVE WEATHER ON A REAL X16:
Download WEATHER-COMMANDER-BRIDGE.zip from the same release.
Start that bridge on your computer and keep it running.
On the X16 open Settings > Wi-Fi and connections > On a real Commander X16.
Join your network, enter the weather computer address, then Get my weather.
This requires a TexElec Serial & ESP32 card with compatible ZiModem firmware.
Physical card operation still needs testing; emulator and protocol checks pass.

Updates, documentation and bridge:
https://github.com/lionsarmor/WEATHER-COMMANDER/releases
'''.encode()
    x16['WEATHER/DATA-NOTICE.TXT'] = ((ROOT / 'assets/data/NOTICE.md').read_text() + '\n' +
                                      (ROOT / 'assets/radar/NOTICE.md').read_text()).encode()
    bridge_paths = ['requirements.txt', 'bridge.sh', 'VERSION', 'docs/HOST-BRIDGE.md',
                    'assets/data/NOTICE.md', 'assets/data/philippines.geojson']
    bridge_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'backend').glob('*.py'))]
    bridge = {'WEATHER-BRIDGE/' + name: ROOT / name for name in bridge_paths}
    bridge['WEATHER-BRIDGE/START-HERE.txt'] = b'''WEATHER COMMANDER - COMPUTER BRIDGE

These files run on your computer. Copy the separate WEATHER folder to the X16.
Install Python 3.12 or newer. In this extracted WEATHER-BRIDGE folder:

  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
  ./bridge.sh

Windows (PowerShell):
  py -3 -m venv .venv
  .venv\\Scripts\\python -m pip install -r requirements.txt
  .venv\\Scripts\\python -m backend.server --bind 0.0.0.0 --output .

Keep the terminal open. Enter the printed computer address in the X16 setup.
No API key is required. See docs/HOST-BRIDGE.md for the guided Wi-Fi steps.
For emulator use, pass --output /path/to/WEATHER to share the extracted X16 folder.
'''
    archives = [('WEATHER-COMMANDER-X16.zip', x16), ('WEATHER-COMMANDER-BRIDGE.zip', bridge)]
    for name, entries in archives:
        destination = ROOT / 'dist' / name
        write_archive(destination, entries)
        print(destination)
    checksums = ''.join(hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name, _ in archives)
    (ROOT / 'dist/SHA256SUMS.txt').write_text(checksums)
    print(f'{len(RUNTIME_FILES)} X16 runtime files; version {version}; SHA256SUMS.txt written.')


if __name__ == '__main__':
    main()
