#!/usr/bin/env python3
"""Run native Wi-Fi setup against modem replies, including failed re-joins."""
from collections import deque
import unittest
from py65.devices.mpu65c02 import MPU
from test_direct_png import labels, ROOT


class Modem(list):
    def __init__(self, join_ok=True, address=b'192.168.1.20', scan_ok=True):
        super().__init__([0]*65536)
        self.rx = deque()
        self.command = bytearray()
        self.commands = []
        self.join_ok, self.address, self.scan_ok = join_ok, address, scan_ok

    def __getitem__(self, address):
        if address == 0x9fe5:
            return 0x20 | bool(self.rx)
        if address == 0x9fe0:
            return self.rx.popleft() if self.rx else 0
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        if address != 0x9fe0:
            return super().__setitem__(address, value)
        if value == 13:
            command = bytes(self.command)
            self.commands.append(command)
            self.command.clear()
            reply = b'OK'
            if command == b'ATI2':
                reply = self.address+b'\r\nOK'
            elif command.startswith(b'ATW"') and not self.join_ok:
                reply = b'ERROR'
            elif command == b'ATW10':
                reply = b'X16-EMULATOR-NET (-40)\r\nOK' if self.scan_ok else b'ERROR'
            self.rx.extend(b'\r\n'+reply+b'\r\n')
        elif value != 10:
            self.command.append(value)


class Flow:
    def __init__(self, **kwargs):
        self.mem = Modem(**kwargs)
        self.cpu = MPU(memory=self.mem)
        self.symbols = labels('network_overlay')
        code = (ROOT/'build/network_overlay.bin').read_bytes()
        self.mem[0xa000:0xa000+len(code)] = code
        self.call(0xa000)
        for name in ('card_present', 'modem_present'):
            self.mem[self.symbols['p8b_network_driver:p8v_'+name]] = 1

    def call(self, address):
        self.cpu.sp = 255
        self.cpu.stPushWord(0x2ff)
        self.cpu.pc = address
        for _ in range(3000000):
            if self.cpu.pc == 0x300:
                return
            if self.mem[self.cpu.pc] == 0xcb:
                self.cpu.pc += 1
            else:
                self.cpu.step()
        raise AssertionError('Wi-Fi action did not finish')

    def action(self, action):
        self.mem[0x69c0] = action
        self.call(0xa003)


class NetworkFlowTests(unittest.TestCase):
    def test_failed_rejoin_cannot_reuse_old_address_and_clears_password(self):
        flow = Flow(join_ok=False)
        flow.mem[0x69c5] = 3
        flow.mem[0x6950:0x6954] = b'new\0'
        flow.mem[0x6980:0x6987] = b'secret\0'
        flow.action(3)
        self.assertEqual(flow.mem[0x69c5], 2)
        self.assertNotIn(b'ATI2', flow.mem.commands)
        self.assertEqual(flow.mem[0x6980:0x69c0], [0]*64)
        self.assertIn(b'COULD NOT JOIN', bytes(flow.mem[0x69d0:0x69f8]))

    def test_only_complete_nonzero_ipv4_means_joined(self):
        for address in (b'4.0.2', b'0.0.0.0', b'999.2.3.4', b'1.2.3.4.5', b'firmware 1.2.3.4', b'ERROR', b'192.168.1.20'):
            with self.subTest(address=address):
                flow = Flow(address=address)
                flow.action(4)
                self.assertEqual(flow.mem[0x69c5], 3 if address==b'192.168.1.20' else 2)

    def test_open_network_join_and_scan_error(self):
        flow = Flow()
        ssid = b'X16-EMULATOR-NET\0'
        flow.mem[0x6950:0x6950+len(ssid)] = ssid
        flow.action(3)
        self.assertEqual(flow.mem[0x69c5], 3)
        self.assertIn(b'ATW"X16-EMULATOR-NET,"', flow.mem.commands)
        flow = Flow(scan_ok=False)
        flow.action(1)
        self.assertIn(b'SCAN FAILED', bytes(flow.mem[0x69d0:0x69f8]))


if __name__ == '__main__':
    unittest.main()
