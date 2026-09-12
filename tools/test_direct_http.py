#!/usr/bin/env python3
"""Execute the actual native HTTP decoder on a 65C02 with adversarial replies."""
import unittest
from pathlib import Path
from py65.devices.mpu65c02 import MPU
ROOT=Path(__file__).resolve().parents[1]

class Decoder:
 def __init__(self,maximum=8192,mode=0):
  self.memory=[0]*65536;self.cpu=MPU(memory=self.memory)
  code=(ROOT/'build/direct_http_overlay.bin').read_bytes()
  self.memory[0xa000:0xa000+len(code)]=code
  self.call(0xa000)
  self.memory[0x6d74:0x6d76]=maximum.to_bytes(2,'little')
  self.memory[0x6d7b]=mode
  self.memory[0x6fff]=0xa5;self.memory[0x9000]=0x5a
  self.call(0xa006)
 def call(self,address):
  self.cpu.sp=0xff;self.cpu.stPushWord(0x2ff);self.cpu.pc=address
  for _ in range(100000):
   if self.cpu.pc==0x300:return
   self.cpu.step()
  raise AssertionError('Native HTTP decoder did not return')
 def feed(self,wire):
  for ch in wire:
   self.memory[0x6d7a]=ch;self.call(0xa009)
  assert self.memory[0x6fff]==0xa5 and self.memory[0x9000]==0x5a
  return self
 @property
 def body(self):
  size=self.memory[0x6d72]+256*self.memory[0x6d73]
  return bytes(self.memory[0x7000:0x7000+size])
 @property
 def complete(self):return bool(self.memory[0x6d78])
 @property
 def failed(self):return bool(self.memory[0x6d79])

class HTTPTests(unittest.TestCase):
 def test_html_prefix_is_explicitly_partial(self):
  decoder=Decoder(32,2).feed(b'HTTP/1.1 200 OK\r\nContent-Length: 95474\r\nSet-Cookie: '+b'x'*700+b'\r\nDate: Sun, 13 Sep 2026 00:00:00 GMT\r\n\r\n'+b'm'*200)
  self.assertTrue(decoder.memory[0x6d7c]);self.assertFalse(decoder.complete)
  self.assertFalse(decoder.failed);self.assertEqual(decoder.body,b'm'*32)
  self.assertEqual(bytes(decoder.memory[0x6ec0:0x6edd]),b'sun, 13 sep 2026 00:00:00 gmt')
 def test_binary_requires_unambiguous_framing(self):
  self.assertTrue(Decoder(65535,1).feed(b'HTTP/1.0 200 OK\r\n\r\n').failed)
 def test_chunked_json_and_trailers(self):
  decoder=Decoder().feed(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n4;name=test\r\n{"a"\r\n3\r\n:1}\r\n0\r\nTrailer: value\r\n\r\n\r\nNO CARRIER\r\n')
  self.assertTrue(decoder.complete);self.assertFalse(decoder.failed)
  self.assertEqual(decoder.body,b'{"a":1}')
 def test_content_length_excludes_modem_result(self):
  decoder=Decoder().feed(b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc\r\nNO CARRIER\r\n')
  self.assertTrue(decoder.complete);self.assertEqual(decoder.body,b'abc')
 def test_close_delimited_document(self):
  decoder=Decoder().feed(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"live":true}\r\nNO CARRIER\r\n')
  self.assertTrue(decoder.complete);self.assertEqual(decoder.body.strip(),b'{"live":true}')
 def test_truncated_chunk_never_completes(self):
  self.assertFalse(Decoder().feed(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n9\r\nshort').complete)
 def test_errors_and_bad_framing_fail(self):
  for wire in (b'HTTP/1.1 429 Too Many Requests\r\n\r\n{}',
               b'HTTP/1.1 200 OK\r\nContent-Length: 9999999\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nx!'):
   with self.subTest(wire=wire):
    result=Decoder().feed(wire);self.assertTrue(result.failed);self.assertFalse(result.complete)
 def test_oversized_payload_cannot_cross_buffer(self):
  for header in (b'Content-Length: 8193\r\n',b'Transfer-Encoding: chunked\r\n'):
   result=Decoder().feed(b'HTTP/1.1 200 OK\r\n'+header+b'\r\n2001\r\n')
   self.assertTrue(result.failed);self.assertFalse(result.complete)
  result=Decoder(8).feed(b'HTTP/1.0 200 OK\r\n\r\n123456789')
  self.assertTrue(result.failed);self.assertEqual(result.body,b'12345678')

if __name__=='__main__':unittest.main()
