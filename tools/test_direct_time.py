#!/usr/bin/env python3
"""Check native HTTP UTC and unsigned Unix timestamps across word boundaries."""
import calendar
from datetime import datetime, timezone
import unittest
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import ROOT

class Clock:
    def __init__(self):
        self.memory = [0]*65536
        self.cpu = MPU(memory=self.memory)
        code = (ROOT/'build/direct_crypto_overlay.bin').read_bytes()
        self.memory[0xa000:0xa000+len(code)] = code
        self.call(0xa000)

    def call(self, address):
        self.cpu.sp = 255
        self.cpu.stPushWord(0x2ff)
        self.cpu.pc = address
        for _ in range(1000000):
            if self.cpu.pc == 0x300:
                return
            self.cpu.step()
        raise AssertionError('Native UTC conversion did not finish')

    @property
    def valid(self):
        return bool(self.memory[0x6ffd])

    @property
    def epoch(self):
        return int.from_bytes(self.memory[0x6ff2:0x6ff6], 'little')

    def date(self, text):
        self.memory[0x6ec0:0x6ee8] = text.encode().ljust(40, b'\0')
        self.call(0xa009)

    def parse(self, text):
        self.memory[0x6e00:0x6e60] = text.encode().ljust(96, b'\0')
        self.memory[0x6e66] = 6
        self.memory[0x6e68] = len(text)
        self.call(0xa00c)

    def format(self):
        self.call(0xa00f)
        return bytes(self.memory[0x6fe0:0x6fec]).split(b'\0', 1)[0].decode()

class TimeTests(unittest.TestCase):
    def test_http_dates_match_utc_without_using_rtc(self):
        for value in (datetime(1970,1,1), datetime(2000,2,29,23,59,59), datetime(2026,9,12,23,45,1), datetime(2099,12,31,23,59,59)):
            clock = Clock()
            clock.date(value.strftime('%a, %d %b %Y %H:%M:%S GMT').lower())
            self.assertTrue(clock.valid)
            expected = calendar.timegm(value.timetuple())
            self.assertEqual(clock.epoch, expected)
            self.assertEqual(clock.format(), str(expected))

    def test_unsigned_epoch_boundaries(self):
        for value in (0,1,65535,65536,1789252813,2147483648,4294967295):
            clock = Clock()
            clock.parse(str(value))
            self.assertTrue(clock.valid)
            self.assertEqual(clock.epoch, value)
            self.assertEqual(clock.format(), str(value))

    def test_bad_dates_and_numeric_overflow_fail(self):
        for text in ('4294967296', '-1', '1e9', '2.5', '', '9999999999'):
            clock = Clock()
            clock.parse(text)
            self.assertFalse(clock.valid, text)
        for text in ('sat, 29 feb 2026 00:00:00 gmt', 'sat, 31 apr 2026 00:00:00 gmt', 'sat, 12 sep 2026 24:00:00 gmt', 'sat, 12 sep 2026 12:00:00 cst', 'sat, 12 sep 2026 12:00 gmt'):
            clock = Clock()
            clock.date(text)
            self.assertFalse(clock.valid, text)

if __name__ == '__main__':
    unittest.main()
