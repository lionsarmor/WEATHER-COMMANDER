#!/usr/bin/env python3
"""Check actual release folders, native dependencies and failed-build safety."""
import hashlib
import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from package import ROOT, RUNTIME_FILES, write_archive


class PackageTests(unittest.TestCase):
    def test_x16_release_is_complete_and_clean(self):
        with ZipFile(ROOT / 'dist/WEATHER-COMMANDER-X16.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {'WEATHER/' + name for name in RUNTIME_FILES} |
                             {'WEATHER/START-HERE.TXT', 'WEATHER/DATA-NOTICE.TXT'})
            runtime = set(RUNTIME_FILES)
            personal = {'WCDATA.BIN', 'WCRLIVE.BIN', 'WCSETUP.BIN', 'WCQUERY.BIN', 'WCCITIES.BIN', 'WCRPNG.BIN'}
            for source in (ROOT / 'src').glob('*.p8'):
                for name in re.findall(r'"(WC[A-Z0-9]+\.BIN)"', source.read_text()):
                    self.assertIn(name, runtime | personal)
            for name in RUNTIME_FILES:
                self.assertEqual(archive.read('WEATHER/' + name), (ROOT / 'dist/sdcard' / name).read_bytes())
                self.assertTrue(archive.read('WEATHER/' + name))

    def test_native_runtime_has_no_bridge_dependency(self):
        with ZipFile(ROOT / 'dist/WEATHER-COMMANDER-X16.zip') as archive:
            setup=archive.read('WEATHER/START-HERE.TXT').decode()
            self.assertIn('No bridge computer',setup)
            self.assertNotIn('BRIDGE.zip',setup)
            self.assertFalse(any(name.endswith('.py') for name in archive.namelist()))
            self.assertTrue({'WCPNG.BIN','WCZLIB.BIN','WCRAPI.BIN','WCWEATH.BIN','WCPBASE.BIN'} <= set(RUNTIME_FILES))
        self.assertNotIn('backend.server',(ROOT/'run.sh').read_text())
        self.assertFalse((ROOT/'dist/WEATHER-COMMANDER-BRIDGE.zip').exists())

    def test_checksums(self):
        for line in (ROOT / 'dist/SHA256SUMS.txt').read_text().splitlines():
            digest, name = line.split()
            self.assertEqual(hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest(), digest)

    def test_missing_bank_preserves_previous_zip_and_archives_are_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            destination = folder / 'release.zip'
            write_archive(destination, {'WEATHER/TEST.BIN': b'bank'})
            original = destination.read_bytes()
            with self.assertRaises(FileNotFoundError):
                write_archive(destination, {'WEATHER/MISSING.BIN': folder / 'missing'})
            self.assertEqual(destination.read_bytes(), original)
            write_archive(destination, {'WEATHER/TEST.BIN': b'bank'})
            self.assertEqual(destination.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
