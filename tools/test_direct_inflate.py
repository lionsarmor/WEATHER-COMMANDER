#!/usr/bin/env python3
"""Run the banked 65C02 decoder against zlib and malformed byte streams."""
import random
import unittest
import zlib
from pathlib import Path
from py65.devices.mpu65c02 import MPU

ROOT = Path(__file__).resolve().parents[1]

class Memory:
    def __init__(self):
        self.low = [0] * 65536
        self.banks = [bytearray(8192) for _ in range(64)]
        self.low[0] = 24

    def __getitem__(self, address):
        if isinstance(address, slice):
            return [self[i] for i in range(*address.indices(65536))]
        if 0xa000 <= address < 0xc000:
            return self.banks[self.low[0]][address - 0xa000]
        return self.low[address]

    def __setitem__(self, address, value):
        if isinstance(address, slice):
            for i, byte in zip(range(*address.indices(65536)), value):
                self[i] = byte
        elif 0xa000 <= address < 0xc000:
            self.banks[self.low[0]][address - 0xa000] = value
        else:
            self.low[address] = value

class Inflater:
    def __init__(self, wire, size):
        self.memory = Memory()
        self.cpu = MPU(memory=self.memory)
        self.wire = wire
        self.position = 0
        self.instructions = 0
        binary = (ROOT / 'build/direct_inflate_overlay.bin').read_bytes()
        self.memory[0xa000:0xa000 + len(binary)] = binary
        self.call(0xa000)
        self.memory[0x6f06:0x6f09] = size.to_bytes(3, 'little')
        self.memory[0x6fff] = 0xa5
        self.memory[0x7601] = 0x5a
        self.call(0xa003)

    def call(self, address):
        cpu, mem = self.cpu, self.memory
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(20000000):
            self.instructions += 1
            if cpu.pc == 0x300:
                return
            if cpu.pc == 0xff6e:
                ret = cpu.stPopWord()
                target = mem[ret + 1] + 256 * mem[ret + 2]
                assert mem[ret + 3] == 3 and target == 0xa009
                if self.position < len(self.wire):
                    mem[0x6f00] = self.wire[self.position]
                    self.position += 1
                else:
                    mem[0x6f01] = 1
                cpu.pc = ret + 4
            elif cpu.pc in (0xff74, 0xff77):
                pointer = cpu.a if cpu.pc == 0xff74 else mem[0x3b2]
                dest = mem[pointer] + 256 * mem[pointer + 1] + cpu.y
                assert 26 <= cpu.x <= 29 and 0xa000 <= dest < 0xc000
                if cpu.pc == 0xff74:
                    cpu.a = mem.banks[cpu.x][dest - 0xa000]
                    cpu.FlagsNZ(cpu.a)
                else:
                    mem.banks[cpu.x][dest - 0xa000] = cpu.a
                cpu.pc = cpu.stPopWord() + 1
            else:
                cpu.step()
        raise AssertionError(f'Decoder failed to return at {cpu.pc:04x}')

    def run(self, chunk=1537):
        result = bytearray()
        while not self.memory[0x6f01] and not self.memory[0x6f09]:
            self.memory[0x6f04:0x6f06] = chunk.to_bytes(2, 'little')
            self.call(0xa006)
            count = self.memory[0x6f02] + 256 * self.memory[0x6f03]
            assert count <= chunk
            result.extend(self.memory[0x7000:0x7000 + count])
        assert self.memory[0x6fff] == 0xa5 and self.memory[0x7601] == 0x5a
        assert self.memory[0] == 24
        return bytes(result)

    @property
    def error(self):
        return self.memory[0x6f01]

class InflateTests(unittest.TestCase):
    def check(self, raw, level=6, strategy=zlib.Z_DEFAULT_STRATEGY, chunk=1537):
        encoder = zlib.compressobj(level, zlib.DEFLATED, 15, 8, strategy)
        wire = encoder.compress(raw) + encoder.flush()
        decoder = Inflater(wire, len(raw))
        self.assertEqual(decoder.run(chunk), raw)
        self.assertEqual(decoder.error, 0)
        self.assertTrue(decoder.memory[0x6f09])
        self.assertEqual(decoder.position, len(wire))

    def test_stored_fixed_and_dynamic(self):
        raw = bytes(range(256)) * 3 + b'weather rain clouds ' * 200
        self.check(raw, 0)
        self.check(raw, strategy=zlib.Z_FIXED, chunk=17)
        self.check(raw)
        self.check(b'')

    def test_history_wrap_and_cross_bank_backreferences(self):
        rng = random.Random(16)
        block = bytes(rng.randrange(32) for _ in range(18000))
        self.check(block + block + b'\0' * 33000)

    def test_truncation_bad_checksum_and_output_limit(self):
        raw = b'RADAR' * 100
        wire = zlib.compress(raw)
        for broken in (wire[:1], wire[:-1], wire[:6], wire[:-1] + bytes([wire[-1] ^ 1]), b'\x78\x20', b'\x78\x9c\x07'):
            with self.subTest(wire=broken):
                decoder = Inflater(broken, len(raw))
                decoder.run()
                self.assertNotEqual(decoder.error, 0)
                self.assertFalse(decoder.memory[0x6f09])
        for limit in (len(raw) - 1, len(raw) + 1):
            decoder = Inflater(wire, limit)
            decoder.run()
            self.assertEqual(decoder.error, 5)

if __name__ == '__main__':
    unittest.main()
