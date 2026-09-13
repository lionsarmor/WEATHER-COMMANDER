#!/usr/bin/env python3
"""Update WEATHER on a mounted X16_SDCARD, preserving personal files."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from package import ROOT, RUNTIME_FILES


def find_card():
    """Use the actual mount table; never write into an unmounted media path."""
    try:
        result = subprocess.run(
            ['findmnt', '--json', '--list', '--output', 'TARGET,LABEL,FSTYPE'],
            check=True, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    cards = [Path(row['target']) for row in json.loads(result.stdout)['filesystems']
             if row.get('label') == 'X16_SDCARD' and row.get('fstype') == 'vfat']
    if len(cards) > 1:
        raise ValueError('Multiple mounted X16_SDCARD cards; leave only the intended card mounted.')
    return cards[0] if cards else None


def install(archive_path, card):
    if not card.is_mount():
        raise ValueError(f'SD card is no longer mounted: {card}')
    expected = set(RUNTIME_FILES) | {'START-HERE.TXT', 'DATA-NOTICE.TXT'}
    # Validate and read the entire package before touching the card.
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(expected) or set(names) != {'WEATHER/' + name for name in expected}:
            raise ValueError('Unexpected or incomplete X16 package; SD card was not changed.')
        contents = {name: archive.read('WEATHER/' + name) for name in expected}
    if not all(contents.values()):
        raise ValueError('Empty package file; SD card was not changed.')
    matches = [path for path in card.iterdir() if path.name.upper() == 'WEATHER']
    if len(matches) > 1:
        raise ValueError('Multiple WEATHER folders on the SD card.')
    destination = matches[0] if matches else card / 'WEATHER'
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError(f'Expected a regular WEATHER folder: {destination}')
    for name in contents:
        target = destination / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f'Expected a regular app file: {target}')
    destination.mkdir(exist_ok=True)
    # Stage all bytes on the card first. A full card cannot truncate installed files.
    with tempfile.TemporaryDirectory(prefix='.weather-update-', dir=destination) as staging:
        for name, data in contents.items():
            with (Path(staging) / name).open('wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        if not card.is_mount():
            raise ValueError('SD card was unmounted during the update.')
        # Install the entry point last; replace only the release's known files.
        for name in sorted(contents, key=lambda name: (name == 'WEATHER.PRG', name)):
            os.replace(Path(staging) / name, destination / name)
    folder_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(folder_fd)
    finally:
        os.close(folder_fd)
    for name, data in contents.items():
        if (destination / name).read_bytes() != data:
            raise OSError(f'SD verification failed: {name}; run WEATHERBUILD again.')
    return destination, len(contents)


def main():
    if os.environ.get('CI'):
        print('SD copy skipped in CI; ZIP is ready.')
        return
    try:
        card = find_card()
        if card is None:
            print('No mounted X16_SDCARD found; ZIP is ready. Insert/mount the card and run WEATHERBUILD again.')
            return
        destination, count = install(ROOT / 'dist/WEATHER-COMMANDER-X16.zip', card)
    except (OSError, ValueError, BadZipFile, subprocess.CalledProcessError) as error:
        print(f'SD copy failed: {error}\nThe built ZIP is still available in dist/.', file=sys.stderr)
        sys.exit(1)
    print(f'SD updated and verified: {destination} ({count} files).')
    print('Saved settings and other files preserved. Eject the card before unplugging it.')


if __name__ == '__main__':
    main()
