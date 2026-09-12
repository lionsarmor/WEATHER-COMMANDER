#!/usr/bin/env python3
"""Check native tile packing, geography and spatial fallback on a banked CPU."""
import random
import unittest
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import Memory, ROOT
from test_direct_png import labels
from build_native_assets import build
from backend.maps import philippines
from backend.radar import LEVELS, checksum

class Renderer:
    def __init__(self, grid, country=0, basemap=None):
        self.memory = Memory()
        self.cpu = MPU(memory=self.memory)
        self.symbols = labels('direct_render_overlay')
        self.basemap = basemap
        self.memory[0] = 23
        code = (ROOT/'build/direct_render_overlay.bin').read_bytes()
        self.memory[0xa000:0xa000+len(code)] = code
        self.call(0xa000)
        self.memory.banks[25][0x600:0x600+4704] = bytes(grid)
        self.memory[0x6f22] = country
        self.memory[0x6f23] = 1
        self.memory[0x6f2a:0x6f2c] = (300).to_bytes(2,'little')
        self.memory[0x6f2c] = 2
        self.memory[0x6fff] = 0xa5
        self.memory[0x9320] = 0x5a

    def word(self, address):
        return self.memory[address]+256*self.memory[address+1]

    def call(self, address):
        cpu,mem,sym = self.cpu,self.memory,self.symbols
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(150000000):
            if cpu.pc == 0x300:
                assert mem[0] == 23
                return
            if cpu.pc == 0xff6e:
                ret = cpu.stPopWord()
                assert self.word(ret+1) == 0xa00c and mem[ret+3] == 3
                cpu.pc = ret+4
            elif cpu.pc in (0xff74,0xff77):
                pointer = cpu.a if cpu.pc == 0xff74 else mem[0x3b2]
                target = self.word(pointer)+cpu.y
                assert cpu.x in (25,26) and 0xa000 <= target < 0xc000
                if cpu.pc == 0xff74:
                    cpu.a = mem.banks[cpu.x][target-0xa000]
                    cpu.FlagsNZ(cpu.a)
                else:
                    mem.banks[cpu.x][target-0xa000] = cpu.a
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == 0xff50:
                mem[2:10] = [126,9,12,23,10,0,0,6]
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['cbm:RDTIM16']:
                cpu.a,cpu.y = 0,0
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['diskio:f_open']:
                cpu.a,cpu.y = int(self.basemap is not None),0
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['diskio:f_close']:
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['diskio:f_read']:
                assert self.word(sym['diskio:f_read:bufferpointer']) == 0x7000
                assert self.word(sym['diskio:f_read:num_bytes']) == 8193
                mem[0x7000:0x7000+len(self.basemap)] = self.basemap
                cpu.a,cpu.y = len(self.basemap) & 255,len(self.basemap)>>8
                cpu.pc = cpu.stPopWord()+1
            else:
                cpu.step()
        raise AssertionError(f'Native packing did not return at {cpu.pc:04x}')

    def run(self):
        self.call(0xa009)
        assert self.memory[0x6fff] == 0xa5 and self.memory[0x9320] == 0x5a
        return bytes(self.memory[0x7000:0x9320])

def unpack(raw):
    assert raw[:4] == b'WCR4'
    assert 0 < raw[4] <= 207
    assert int.from_bytes(raw[12:14],'little') == checksum(raw)
    pixels = bytearray(336*224)
    for row in range(28):
        for col in range(42):
            address = 6640+row*84+col*2
            word = int.from_bytes(raw[address:address+2],'little')
            index = (word & 1023)-257
            assert word & 0xfc00 == 0xf000 and 0 <= index < raw[4]
            for i in range(32):
                value = raw[16+index*32+i]
                target = (row*8+i//4)*336+col*8+(i % 4)*2
                pixels[target:target+2] = bytes([value>>4,value & 15])
    return pixels

class RenderTests(unittest.TestCase):
    def test_isolated_echoes_keep_their_coordinates(self):
        grid = bytearray(4704)
        grid[10*84+8] = 5
        grid[40*84+61] = 2
        renderer = Renderer(grid)
        raw = renderer.run()
        self.assertEqual(renderer.memory[0x6f2c],3)
        self.assertEqual(raw[6:11],bytes([126,9,12,23,5]))
        expected = bytearray(336*224)
        for x,y,level in ((8,10,5),(61,40,2)):
            for dy in range(4):
                expected[(y*4+dy)*336+x*4:(y*4+dy)*336+x*4+4] = bytes([LEVELS[level-1]])*4
        self.assertEqual(unpack(raw),expected)

    def test_ph_basemap_is_preserved_without_returns(self):
        renderer = Renderer(bytes(4704),1,build())
        raw = renderer.run()
        self.assertEqual(renderer.memory[0x6f2c],3)
        self.assertEqual(unpack(raw),philippines().tobytes())

    def test_codebook_overflow_coarsens_in_place(self):
        rng = random.Random(16)
        grid = bytearray(rng.randrange(8) if x<60 else 0 for y in range(56) for x in range(84))
        renderer = Renderer(grid)
        raw = renderer.run()
        self.assertEqual(renderer.memory[0x6f2c],3)
        self.assertEqual(renderer.memory[0x6f2d],8)
        expected = bytearray(336*224)
        for y in range(28):
            for x in range(42):
                level = max(grid[(y*2+dy)*84+x*2+dx] for dy in range(2) for dx in range(2))
                color = LEVELS[level-1] if level else 0
                for dy in range(8):
                    start = (y*8+dy)*336+x*8
                    expected[start:start+8] = bytes([color])*8
        self.assertEqual(unpack(raw),expected)

if __name__ == '__main__':
    unittest.main()
