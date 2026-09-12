#!/usr/bin/env python3
"""Exercise the actual banked PNG/DEFLATE pair against Pillow and bad images."""
import io
import struct
import unittest
import zlib
from PIL import Image
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import Memory, ROOT

def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))

def png(width, height, color, rows, extra=b'', split=False):
    data = zlib.compress(rows)
    pieces = [data[i:i+7] for i in range(0, len(data), 7)] if split else [data]
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, color, 0, 0, 0))
            + extra + b''.join(chunk(b'IDAT', piece) for piece in pieces) + chunk(b'IEND', b''))

def labels(name):
    return {parts[2].lstrip('.'): int(parts[1], 16)
            for line in (ROOT / 'build' / (name + '.vice-mon-list')).read_text().splitlines()
            if len(parts := line.split()) >= 3 and parts[0] == 'al'}

class PNGDecoder:
    def __init__(self, wire):
        self.memory = Memory()
        self.cpu = MPU(memory=self.memory)
        self.wire = wire
        self.position = 0
        self.closed = True
        self.instructions = 0
        self.fars = []
        self.symbols = labels('direct_png_overlay')
        for bank, name in ((3, 'direct_png'), (24, 'direct_inflate')):
            self.memory[0] = bank
            code = (ROOT / 'build' / (name + '_overlay.bin')).read_bytes()
            self.memory[0xa000:0xa000 + len(code)] = code
            self.call(bank, 0xa000)
        self.memory[0x6fff] = 0xa5
        self.memory[0x7601] = 0x5a
        self.memory.banks[25][1536] = 0xc3
        self.call(3, 0xa003)

    def word(self, address):
        return self.memory[address] + 256 * self.memory[address + 1]

    def call(self, bank, address):
        cpu, mem = self.cpu, self.memory
        mem[0] = bank
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(20000000):
            self.instructions += 1
            if cpu.pc == 0x300:
                assert mem[0] == bank and not self.fars
                return
            if cpu.pc == 0xff6e:
                ret = cpu.stPopWord()
                target, dest_bank = self.word(ret + 1), mem[ret + 3]
                assert dest_bank in (3, 24)
                self.fars.append((mem[0], ret + 4))
                mem[0] = dest_bank
                cpu.stPushWord(0xfeff)
                cpu.pc = target
            elif cpu.pc == 0xff00:
                mem[0], cpu.pc = self.fars.pop()
            elif cpu.pc in (0xff74, 0xff77):
                pointer = cpu.a if cpu.pc == 0xff74 else mem[0x3b2]
                dest = self.word(pointer) + cpu.y
                assert 25 <= cpu.x <= 29 and 0xa000 <= dest < 0xc000
                if cpu.pc == 0xff74:
                    cpu.a = mem.banks[cpu.x][dest - 0xa000]
                    cpu.FlagsNZ(cpu.a)
                else:
                    mem.banks[cpu.x][dest - 0xa000] = cpu.a
                cpu.pc = cpu.stPopWord() + 1
            elif mem[0] == 3 and cpu.pc == self.symbols['diskio:f_open']:
                self.position = 0
                self.closed = False
                cpu.a, cpu.y = 1, 0
                cpu.pc = cpu.stPopWord() + 1
            elif mem[0] == 3 and cpu.pc == self.symbols['diskio:f_close']:
                self.closed = True
                cpu.pc = cpu.stPopWord() + 1
            elif mem[0] == 3 and cpu.pc == self.symbols['diskio:f_read']:
                pointer = self.word(self.symbols['diskio:f_read:bufferpointer'])
                count = self.word(self.symbols['diskio:f_read:num_bytes'])
                assert pointer == self.symbols['p8b_direct_png:p8v_file_buffer'] and count in (1, 256)
                assert not self.closed
                body = self.wire[self.position:self.position + count]
                mem[pointer:pointer + len(body)] = body
                self.position += len(body)
                cpu.a, cpu.y = len(body) & 255, len(body) >> 8
                cpu.pc = cpu.stPopWord() + 1
            else:
                cpu.step()
        raise AssertionError(f'PNG decoder did not return at bank {mem[0]}:{cpu.pc:04x}')

    def run(self, pixels=False):
        result = bytearray()
        while not self.memory[0x6f01] and not self.memory[0x6f1b]:
            self.call(3, 0xa006)
            if not self.memory[0x6f1a]:
                continue
            if pixels:
                for i in range(self.word(0x6f10)):
                    self.memory[0x6f1c:0x6f1e] = i.to_bytes(2, 'little')
                    self.call(3, 0xa00f)
                    result.extend(self.memory[0x6f1e:0x6f22])
            else:
                result.extend(self.memory[0x7001:0x7001 + self.word(0x6f14)])
        assert self.memory[0x6fff] == 0xa5 and self.memory[0x7601] == 0x5a
        assert self.memory.banks[25][1536] == 0xc3
        self.call(3, 0xa00c)
        assert self.closed
        return bytes(result)

class PNGTests(unittest.TestCase):
    def test_pillow_formats_and_transparency(self):
        for mode in ('L', 'LA', 'RGB', 'RGBA', 'P'):
            image = Image.new(mode, (16, 12))
            bands = len(image.getbands())
            for y in range(image.height):
                for x in range(image.width):
                    value = tuple((x*17+y*23+i*61) % 256 for i in range(bands))
                    image.putpixel((x, y), value[0] if bands == 1 else value)
            options = {}
            if mode == 'P':
                image.putpalette(bytes(range(256))*3)
                options['transparency'] = bytes(range(256))
            elif mode in ('L', 'RGB'):
                options['transparency'] = image.getpixel((0, 0))
            output = io.BytesIO()
            image.save(output, format='PNG', **options)
            with self.subTest(mode=mode):
                wire = output.getvalue()
                decoder = PNGDecoder(wire)
                self.assertEqual(decoder.run(True), Image.open(io.BytesIO(wire)).convert('RGBA').tobytes())
                self.assertEqual(decoder.memory[0x6f01], 0)
                self.assertTrue(decoder.memory[0x6f1b])

    def test_all_filters_split_idat_and_previous_row(self):
        width, height, channels = 20, 10, 2
        previous = bytes(width*channels)
        filtered, expected = bytearray(), bytearray()
        for y in range(height):
            current = bytes((i*11+y*37) % 256 for i in range(width*channels))
            mode = y % 5
            filtered.append(mode)
            for i, value in enumerate(current):
                a = current[i-channels] if i >= channels else 0
                b = previous[i]
                c = previous[i-channels] if i >= channels else 0
                p = a+b-c
                nearest = min((a, b, c), key=lambda candidate: abs(p-candidate))
                prediction = (0, a, b, (a+b)//2, nearest)[mode]
                filtered.append((value-prediction) & 255)
            expected.extend(current)
            previous = current
        decoder = PNGDecoder(png(width, height, 4, filtered, split=True))
        self.assertEqual(decoder.run(), expected)
        self.assertEqual(decoder.memory[0x6f01], 0)
        self.assertTrue(decoder.memory[0x6f1b])

    def test_invalid_images_never_complete(self):
        valid = png(2, 2, 0, b'\0\1\2\0\3\4')
        damaged = bytearray(valid)
        damaged[29] ^= 1
        for wire in (valid[:-1], valid+b'x', bytes(damaged), png(1, 1, 0, b'\0\0'),
                     png(1537, 2, 0, b''), png(2, 2, 0, b'\5\1\2\0\3\4'),
                     png(2, 2, 0, b'\0\1\2'), png(2, 2, 3, b'\0\1\2\0\3\4')):
            with self.subTest(wire=wire[:40]):
                decoder = PNGDecoder(wire)
                decoder.run()
                self.assertNotEqual(decoder.memory[0x6f01], 0)
                self.assertFalse(decoder.memory[0x6f1b])

if __name__ == '__main__':
    unittest.main()
