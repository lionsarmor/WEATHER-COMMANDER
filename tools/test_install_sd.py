#!/usr/bin/env python3
"""Exercise SD updates without requiring or writing to a real card."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from install_sd import find_card, install
from package import RUNTIME_FILES


class SDInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.card = self.root / 'card'
        self.card.mkdir()
        self.archive = self.root / 'weather.zip'
        with ZipFile(self.archive, 'w') as archive:
            for name in RUNTIME_FILES + ['START-HERE.TXT', 'DATA-NOTICE.TXT']:
                archive.writestr('WEATHER/' + name, ('new ' + name).encode())

    def test_updates_existing_folder_and_preserves_personal_files(self):
        folder = self.card / 'weather'
        folder.mkdir()
        (folder / 'WEATHER.PRG').write_bytes(b'old app')
        (folder / 'WCSETUP.BIN').write_bytes(b'my preferences')
        (folder / 'WCRPNG.BIN').write_bytes(b'my radar')
        (self.card / 'DESKCMD.PRG').write_bytes(b'my launcher')
        with patch.object(Path, 'is_mount', return_value=True):
            destination, count = install(self.archive, self.card)
        self.assertEqual(destination, folder)
        self.assertEqual(count, len(RUNTIME_FILES) + 2)
        self.assertEqual((folder / 'WEATHER.PRG').read_bytes(), b'new WEATHER.PRG')
        self.assertEqual((folder / 'WCSETUP.BIN').read_bytes(), b'my preferences')
        self.assertEqual((folder / 'WCRPNG.BIN').read_bytes(), b'my radar')
        self.assertEqual((self.card / 'DESKCMD.PRG').read_bytes(), b'my launcher')
        self.assertFalse(list(folder.glob('.weather-update-*')))

    def test_unmounted_path_is_not_written(self):
        with self.assertRaisesRegex(ValueError, 'no longer mounted'):
            install(self.archive, self.card)
        self.assertEqual(list(self.card.iterdir()), [])

    def test_unexpected_archive_entry_is_rejected_before_writing(self):
        with ZipFile(self.archive, 'a') as archive:
            archive.writestr('WEATHER/../WCSETUP.BIN', b'bad')
        with patch.object(Path, 'is_mount', return_value=True):
            with self.assertRaisesRegex(ValueError, 'Unexpected'):
                install(self.archive, self.card)
        self.assertEqual(list(self.card.iterdir()), [])

    def test_failed_staging_preserves_installed_app(self):
        folder = self.card / 'WEATHER'
        folder.mkdir()
        (folder / 'WEATHER.PRG').write_bytes(b'old app')
        with patch.object(Path, 'is_mount', return_value=True), patch('install_sd.os.fsync', side_effect=OSError('card full')):
            with self.assertRaisesRegex(OSError, 'card full'):
                install(self.archive, self.card)
        self.assertEqual((folder / 'WEATHER.PRG').read_bytes(), b'old app')
        self.assertEqual([path.name for path in folder.iterdir()], ['WEATHER.PRG'])

    def test_symlink_folder_is_not_followed(self):
        (self.card / 'WEATHER').symlink_to(self.root, target_is_directory=True)
        with patch.object(Path, 'is_mount', return_value=True):
            with self.assertRaisesRegex(ValueError, 'regular WEATHER folder'):
                install(self.archive, self.card)
        self.assertFalse((self.root / 'WEATHER.PRG').exists())

    def test_discovery_requires_one_mounted_x16_fat_card(self):
        unrelated = {'target': '/media/backup', 'label': 'BACKUP', 'fstype': 'vfat'}
        x16 = {'target': '/media/X16_SDCARD', 'label': 'X16_SDCARD', 'fstype': 'vfat'}
        with patch('install_sd.subprocess.run') as run:
            run.return_value.stdout = json.dumps({'filesystems': [unrelated]})
            self.assertIsNone(find_card())
            run.return_value.stdout = json.dumps({'filesystems': [unrelated, x16]})
            self.assertEqual(find_card(), Path('/media/X16_SDCARD'))
            run.return_value.stdout = json.dumps({'filesystems': [x16, dict(x16, target='/media/second')]})
            with self.assertRaisesRegex(ValueError, 'Multiple mounted'):
                find_card()


if __name__ == '__main__':
    unittest.main()
