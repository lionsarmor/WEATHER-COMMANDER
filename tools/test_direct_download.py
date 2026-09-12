#!/usr/bin/env python3
"""Run native ATDS + HTTP + bounded SD writes with a simulated UART/drive."""
from collections import deque
import unittest
from py65.devices.mpu65c02 import MPU
from test_direct_png import labels
from test_direct_inflate import ROOT

class UARTMemory(list):
    def __init__(self, wire):
        super().__init__([0]*65536)
        self.wire = wire
        self.rx = deque()
        self.command = bytearray()
        self.request = bytearray()
        self.commands = []
        self.stream = False
        self[0x9fe4] = 0x27

    def __getitem__(self, address):
        if address == 0x9fe5:
            return 0x20 | bool(self.rx)
        if address == 0x9fe0:
            return self.rx.popleft() if self.rx else 0
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        if address != 0x9fe0:
            return super().__setitem__(address, value)
        if self.stream:
            if value == 10 and not self.request:
                return
            self.request.append(value)
            if self.request.endswith(b'\r\n\r\n'):
                self.rx.extend(self.wire + b'\r\nNO CARRIER\r\n')
                self.stream = False
        elif value == 13:
            command = bytes(self.command)
            self.commands.append(command)
            self.command.clear()
            if command.startswith(b'ATDS'):
                self.stream = True
                self.rx.extend(b'\r\nCONNECT 1\r\n')
            else:
                self.rx.extend(b'\r\nOK\r\n')
        elif value != 10:
            self.command.append(value)
            if self.command == b'+++':
                self.command.clear()

class Download:
    def __init__(self, wire, mode=1, maximum=65535, disk_failure=False, request=None):
        mem = self.memory = UARTMemory(wire)
        cpu = self.cpu = MPU(memory=mem)
        self.disk = bytearray()
        self.opened = False
        self.disk_failure = disk_failure
        self.symbols = labels('direct_http_overlay')
        binary = (ROOT/'build/direct_http_overlay.bin').read_bytes()
        mem[0xa000:0xa000+len(binary)] = binary
        self.call(0xa000)
        host = b'panahon.gov.ph\0'
        mem[0x6d80:0x6d80+len(host)] = host
        request = request or b'GET /public-radar.png HTTP/1.1\r\nHost: panahon.gov.ph\r\nConnection: close\r\n\r\n'
        mem[0x8000:0x8000+len(request)] = request
        mem[0x6d70:0x6d72] = len(request).to_bytes(2, 'little')
        mem[0x6d74:0x6d76] = maximum.to_bytes(2, 'little')
        mem[0x6d7b] = mode
        mem[0x6fff] = 0xa5
        mem[0x9000] = 0x5a
        self.call(0xa003)
        assert not self.opened
        assert mem[0x6fff] == 0xa5 and mem[0x9000] == 0x5a
        assert mem[0x9fe4] == 0x27

    def word(self, address):
        return self.memory[address] + 256*self.memory[address+1]

    def call(self, address):
        cpu, mem, sym = self.cpu, self.memory, self.symbols
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(20000000):
            if cpu.pc == 0x300:
                return
            if cpu.pc == sym['diskio:f_open_w']:
                self.opened = True
                cpu.a, cpu.y = 1, 0
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['diskio:f_close_w']:
                self.opened = False
                cpu.pc = cpu.stPopWord()+1
            elif cpu.pc == sym['diskio:f_write']:
                assert self.opened
                assert mem[0x9fe4] & 0x22 == 0, 'RTS must stop the modem during an SD write'
                pointer = self.word(sym['diskio:f_write:bufferpointer'])
                count = self.word(sym['diskio:f_write:num_bytes'])
                assert pointer == 0x7000 and 0 < count <= 512
                okay = not self.disk_failure or len(self.disk) < 512
                if okay:
                    self.disk.extend(mem[pointer:pointer+count])
                cpu.a, cpu.y = int(okay), 0
                cpu.pc = cpu.stPopWord()+1
            elif mem[cpu.pc] == 0xcb:
                cpu.pc += 1
            else:
                cpu.step()
        raise AssertionError(f'Native download did not return at {cpu.pc:04x}')

class DownloadTests(unittest.TestCase):
    def test_long_request_chunked_image_and_disk_flow_control(self):
        raw = bytes(range(256))*60 + b'\r\nNO CARRIER\r\n'
        wire = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
        wire += b''.join(f'{len(raw[i:i+511]):x}\r\n'.encode()+raw[i:i+511]+b'\r\n' for i in range(0, len(raw), 511))
        wire += b'0\r\n\r\n'
        request = b'GET /export?projection='+b'x'*1800+b' HTTP/1.1\r\nHost: panahon.gov.ph\r\n\r\n'
        result = Download(wire, request=request)
        self.assertEqual(result.disk, raw)
        self.assertTrue(result.memory[0x6d78])
        self.assertFalse(result.memory[0x6d79])
        self.assertEqual(result.memory.request, request)
        self.assertEqual(result.memory.commands, [b'ATDS"panahon.gov.ph:443"'])

    def test_disk_failure_and_truncation_never_succeed(self):
        wire = b'HTTP/1.1 200 OK\r\nContent-Length: 2048\r\n\r\n'+b'x'*2048
        for body, disk_failure in ((wire, True), (wire[:-1000], False)):
            with self.subTest(disk_failure=disk_failure):
                result = Download(body, disk_failure=disk_failure)
                self.assertTrue(result.memory[0x6d79])
                self.assertFalse(result.memory[0x6d78])

    def test_ram_response_can_replace_sent_request(self):
        raw = b'['+b'123,'*1500+b'0]'
        result = Download(b'HTTP/1.0 200 OK\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw, mode=0, maximum=8192)
        self.assertFalse(result.memory[0x6d79])
        self.assertTrue(result.memory[0x6d78])
        self.assertEqual(bytes(result.memory[0x7000:0x7000+len(raw)]), raw)
        self.assertEqual(result.disk, b'')

if __name__ == '__main__':
    unittest.main()
