#!/usr/bin/env python3
"""Exercise the native JSON parser with API-shaped and malformed documents."""
import json,unittest
from pathlib import Path
from py65.devices.mpu65c02 import MPU
ROOT=Path(__file__).resolve().parents[1]
class Parser:
 def __init__(self,raw):
  self.memory=[0]*65536;self.cpu=MPU(memory=self.memory)
  data=(ROOT/'build/direct_weather_decode_overlay.bin').read_bytes()
  self.memory[0xa000:0xa000+len(data)]=data;self.call(0xa000)
  self.memory[0x7000:0x7000+len(raw)]=raw
  self.memory[0x6d72:0x6d74]=len(raw).to_bytes(2,'little');self.call(0xa006)
 def call(self,address):
  self.cpu.sp=255;self.cpu.stPushWord(0x2ff);self.cpu.pc=address
  for _ in range(1000000):
   if self.cpu.pc==0x300:return
   self.cpu.step()
  raise AssertionError('JSON parser failed to return')
 @property
 def failed(self):return bool(self.memory[0x6e67])
 @property
 def kind(self):return self.memory[0x6e66]
 @property
 def text(self):return bytes(self.memory[0x6e00:0x6e00+self.memory[0x6e68]])
 @property
 def start(self):return self.memory[0x6e62]+256*self.memory[0x6e63]
 def find(self,key,scope=0):
  self.memory[0x6e80:0x6eb0]=key.encode().ljust(48,b'\0')
  self.memory[0x6e6a:0x6e6c]=scope.to_bytes(2,'little')
  self.call(0xa009)
  return bool(self.memory[0x6e6c])

class JSONTests(unittest.TestCase):
 def test_current_values_do_not_match_units(self):
  parser=Parser(b'{"current_units":{"temperature":"F"},"current":{"temperature":-12.5,"is_day":0},"daily":{"temperature":[1,2,3]}}')
  self.assertFalse(parser.failed);self.assertTrue(parser.find('current'));self.assertEqual(parser.kind,1)
  scope=parser.start
  self.assertTrue(parser.find('temperature',scope));self.assertEqual(parser.text,b'-12.5')
  self.assertTrue(parser.find('is_day',scope));self.assertEqual(parser.text,b'0')
  self.assertFalse(parser.find('absent',scope));self.assertFalse(parser.failed)
 def test_arrays_strings_literals_and_escapes(self):
  for value in [None,True,False,{},[],[1,-2.5,1e-6,'a\\b\nc'],{'city':'Sao Paulo','escaped':'quote"slash/','unicode':'Cebu \u2600'}]:
   with self.subTest(value=value):self.assertFalse(Parser(json.dumps(value).encode()).failed)
  parser=Parser(b'{"text":"CHI\\u0043AGO"}')
  self.assertTrue(parser.find('text'));self.assertEqual(parser.text,b'CHICAGO')
 def test_malformed_documents_are_rejected(self):
  for raw in [b'',b'{',b'[1,]',b'{"a":}',b'{"a":1,}',b'{a:1}',b'[01]',b'[1.]',b'[1e]',b'true false',b'{"a" 1}',b'"unterminated',b'"bad\\q"',b'"bad\\uZZZZ"',b'"bad\x01"',b'{"a":null]']:
   with self.subTest(raw=raw):self.assertTrue(Parser(raw).failed)
 def test_depth_is_bounded(self):
  self.assertTrue(Parser(b'['*17+b'0'+b']'*17).failed)
  self.assertFalse(Parser(b'['*15+b'0'+b']'*15).failed)
 def test_partial_and_oversized_numeric_fields(self):
  self.assertTrue(Parser(b'{"temperature":'+b'1'*100+b'}').failed)
  self.assertTrue(Parser(b'{"temperature":12').failed)

if __name__=='__main__':unittest.main()
