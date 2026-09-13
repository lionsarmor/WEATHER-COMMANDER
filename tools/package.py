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
RUNTIME_FILES += ['WCPBASE.BIN','WCDMUS.BIN','WCDMPH.BIN']


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
Use a compatible TexElec Serial & ESP32 / ZiModem card at IO7 ($9FE0).
Open Settings > Wi-Fi and connections > On a real Commander X16.
Choose your network, enter its password, then Get my weather.
Save and open weather stores display preferences and personal city coordinates.
No bridge computer, API key or custom card firmware is required.

The card requests Open-Meteo forecasts and NOAA/PAGASA radar directly.
Philippine radar builds in the background and takes about five minutes at
8 MHz. Other screens and controls remain available while it decodes.
Outdated, malformed or unavailable radar images are never presented as live.
Demo mode has sample forecasts and recorded radar for both countries.

Validated in ROM r49 emulation and compiled protocol tests. A physical-card
end-to-end test has not been performed.

Updates and documentation:
https://github.com/lionsarmor/WEATHER-COMMANDER/releases
'''.encode()
    x16['WEATHER/DATA-NOTICE.TXT'] = ((ROOT / 'assets/data/NOTICE.md').read_text() + '\n' +
                                      (ROOT / 'assets/radar/NOTICE.md').read_text()).encode()
    archives = [('WEATHER-COMMANDER-X16.zip', x16)]
    for name, entries in archives:
        destination = ROOT / 'dist' / name
        write_archive(destination, entries)
        print(destination)
    # Retire the old generated bridge download only after the X16 ZIP succeeds.
    (ROOT / 'dist/WEATHER-COMMANDER-BRIDGE.zip').unlink(missing_ok=True)
    checksums = ''.join(hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name, _ in archives)
    (ROOT / 'dist/SHA256SUMS.txt').write_text(checksums)
    print(f'{len(RUNTIME_FILES)} X16 runtime files; version {version}; SHA256SUMS.txt written.')


if __name__ == '__main__':
    main()
