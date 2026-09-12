#!/usr/bin/env python3
"""Native SHA-256/HMAC known-answer tests, including PAGASA-sized grants."""
import hashlib
import hmac
import unittest
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import ROOT

def digest(message, key=None):
    memory = [0]*65536
    cpu = MPU(memory=memory)
    binary = (ROOT/'build/direct_crypto_overlay.bin').read_bytes()
    memory[0xa000:0xa000+len(binary)] = binary
    def call(address):
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(20000000):
            if cpu.pc == 0x300:
                return
            cpu.step()
        raise AssertionError('Native signing did not finish')
    call(0xa000)
    memory[0x7000:0x7000+len(message)] = message
    memory[0x6fed:0x6fef] = len(message).to_bytes(2, 'little')
    memory[0x6fef:0x6ff1] = b'\0\x70'
    if key is not None:
        assert len(key) <= 96
        memory[0x6f40:0x6f40+len(key)] = key
        memory[0x6fec] = len(key)
    call(0xa006 if key is None else 0xa003)
    assert memory[0x6ff1]
    return bytes(memory[0x6fa0:0x6fc0])

class CryptoTests(unittest.TestCase):
    def test_sha_known_answers_and_padding_boundaries(self):
        for value in (b'', b'abc', b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'):
            with self.subTest(value=value):
                self.assertEqual(digest(value), hashlib.sha256(value).digest())
        for size in (55, 56, 63, 64, 65, 127, 1023):
            with self.subTest(size=size):
                value = bytes(i % 256 for i in range(size))
                self.assertEqual(digest(value), hashlib.sha256(value).digest())

    def test_hmac_short_long_and_public_session_keys(self):
        message = b'GET\napi/v1/radar-data-image\n1789252813\n0123456789abcdef0123456789abcdef'
        for key in (b'', b'key', b'\x0b'*20, b'x'*64, b'y'*65, b'z'*91, bytes(range(96))):
            with self.subTest(key_size=len(key)):
                self.assertEqual(digest(message, key), hmac.new(key, message, hashlib.sha256).digest())

if __name__ == '__main__':
    unittest.main()
