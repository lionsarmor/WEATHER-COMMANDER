#!/usr/bin/env python3
"""Exercise native radar requests, metadata validation and public-session HMAC.

--live runs the compiled request builder/signing against the public services.
The test transport supplies HTTP/file I/O; test_direct_download separately runs
the real native UART/HTTP/SD transport. No bridge wire format is involved.
"""
import hashlib
import hmac
import json
import sys
import unittest
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import Memory, ROOT

NOW = int(datetime(2026,9,12,23,10,tzinfo=timezone.utc).timestamp())
DATE = 'sat, 12 sep 2026 23:10:00 gmt'
KEY = b'K'*91
CSRF = b'C'*40
GRANT = b'G'*91

def ph_metadata(stamp=NOW-300):
    return {'success':True, 'data':{'no_data':False, 'tile_version':5,
        'bounds':[115.41549141305251,3.801613036809332,129.51730887177652,22.45850950564088],
        'scale':{'mode':'rain','max':80,'sqrt':True,'unit':'mm/hr'},
        'timeline':[{'observed_at_unix':NOW-1200}, {'observed_at_unix':stamp}]}}

class Radar:
    def __init__(self, country, transport=None):
        self.memory = Memory()
        self.cpu = MPU(memory=self.memory)
        self.fars = []
        self.requests = []
        self.image = None
        self.noise = 0
        self.transport = transport or self.fixture
        self.ph = ph_metadata()
        self.us = {'features':[{'attributes':{'objectid':123456789, 'idp_validtime':(NOW-300)*1000}}]}
        for bank, module in ((1,'direct_radar'), (2,'direct_crypto'), (21,'direct_weather_decode')):
            self.memory[0] = bank
            code = (ROOT/'build'/(module+'_overlay.bin')).read_bytes()
            self.memory[0xa000:0xa000+len(code)] = code
            self.call(bank, 0xa000)
        self.memory[0x6f22] = country

    def word(self, address):
        return self.memory[address]+256*self.memory[address+1]

    def fixture(self, path, headers):
        url = urllib.parse.urlsplit(path)
        query = urllib.parse.parse_qs(url.query)
        if url.path == '/':
            return (b'<html><meta name="csrf-token" content="'+CSRF+b'"><meta name="api-sig" content="'+KEY+b'"><meta name="embed-grant" content="'+GRANT+b'">'+b' '*2000), DATE
        if url.path.startswith('/api/'):
            assert query['token'] == [CSRF.decode()]
            assert headers['x-embed-grant'] == GRANT.decode()
            value = '\n'.join(['GET',url.path.lstrip('/'),headers['x-ts'],headers['x-nonce']]).encode()
            assert headers['x-sig'] == hmac.new(KEY,value,hashlib.sha256).hexdigest()
            assert int(headers['x-ts']) == NOW
            assert len(headers['x-nonce']) == 32
            if url.path.endswith('/timeline'):
                return json.dumps(self.ph).encode(), DATE
            assert query['t'] == [str(max(x['observed_at_unix'] for x in self.ph['data']['timeline']))]
            assert query['size'] == ['1024'] and query['mode'] == ['rain']
            return b'fixture-PAGASA-PNG', DATE
        if url.path.endswith('/query'):
            assert query['where'] == ["idp_subset='CONUS'"]
            return json.dumps(self.us).encode(), DATE
        assert url.path.endswith('/exportImage')
        assert query['size'] == ['84,56']
        assert query['imageSR'] == query['bboxSR']
        assert '6371000' in json.loads(query['imageSR'][0])['wkt']
        assert json.loads(query['mosaicRule'][0])['lockRasterIds'] == [123456789]
        return b'fixture-NOAA-PNG', DATE

    def exchange(self):
        mem = self.memory
        size = self.word(0x6d70)
        assert 0 < size <= 4095
        request = bytes(mem[0x8000:0x8000+size]).decode('ascii')
        assert request.endswith('\r\n\r\n')
        lines = request.split('\r\n')
        method,path,version = lines[0].split(' ')
        assert method == 'GET' and version == 'HTTP/1.1'
        headers = dict((name.lower(),value.strip()) for line in lines[1:] if line for name,_,value in [line.partition(':')])
        self.requests.append((path,headers))
        raw,date = self.transport(path,headers)
        maximum = self.word(0x6d74)
        mode = mem[0x6d7b]
        mem[0x6d76:0x6d78] = (200).to_bytes(2,'little')
        mem[0x6d79] = 0
        mem[0x6d7c] = int(mode == 2 and len(raw) >= maximum)
        mem[0x6d78] = int(not mem[0x6d7c])
        raw = raw[:maximum] if mode == 2 else raw
        assert len(raw) <= maximum
        mem[0x6d72:0x6d74] = len(raw).to_bytes(2,'little')
        mem[0x6ec0:0x6ee8] = date.lower().encode().ljust(40,b'\0')
        if mode == 1:
            self.image = raw
        else:
            mem[0x7000:0x7000+len(raw)] = raw

    def call(self, bank, address):
        cpu,mem = self.cpu,self.memory
        mem[0] = bank
        cpu.sp = 255
        cpu.stPushWord(0x2ff)
        cpu.pc = address
        for _ in range(40000000):
            if cpu.pc == 0x300:
                assert mem[0] == bank and not self.fars
                return
            if cpu.pc == 0xff6e:
                ret = cpu.stPopWord()
                target,dest = self.word(ret+1),mem[ret+3]
                if dest == 20:
                    assert target == 0xa003
                    self.exchange()
                    cpu.pc = ret+4
                else:
                    assert dest in (1,2,21)
                    self.fars.append((mem[0],ret+4))
                    mem[0] = dest
                    cpu.stPushWord(0xfeff)
                    cpu.pc = target
            elif cpu.pc == 0xff00:
                mem[0],cpu.pc = self.fars.pop()
            elif cpu.pc == 0xfecf:
                self.noise = (self.noise+37) % 256
                cpu.a,cpu.x,cpu.y = self.noise,0,0
                cpu.pc = cpu.stPopWord()+1
            else:
                cpu.step()
        raise AssertionError(f'Native radar did not return at bank {mem[0]}:{cpu.pc:04x}')

    def run(self):
        self.call(1,0xa003)
        return bool(self.memory[0x6f23])

class RadarTests(unittest.TestCase):
    def test_native_noaa_query_locks_raster_and_projection(self):
        radar = Radar(0)
        self.assertTrue(radar.run())
        self.assertEqual(radar.image,b'fixture-NOAA-PNG')
        self.assertEqual(len(radar.requests),2)
        self.assertEqual(radar.word(0x6f2a),300)

    def test_public_session_signed_timeline_and_latest_image(self):
        radar = Radar(1)
        self.assertTrue(radar.run())
        self.assertEqual(radar.image,b'fixture-PAGASA-PNG')
        self.assertEqual(len(radar.requests),3)
        self.assertNotEqual(radar.requests[1][1]['x-nonce'],radar.requests[2][1]['x-nonce'])

    def test_stale_future_and_changed_geography_are_rejected(self):
        cases = [('stale',0),('future',0),('bounds',1),('scale',1)]
        for name,country in cases:
            radar = Radar(country)
            if name == 'stale':
                radar.us['features'][0]['attributes']['idp_validtime'] = (NOW-901)*1000
            elif name == 'future':
                radar.us['features'][0]['attributes']['idp_validtime'] = (NOW+1)*1000
            elif name == 'bounds':
                radar.ph['data']['bounds'][0] = 114.5
            else:
                radar.ph['data']['scale']['sqrt'] = False
            with self.subTest(name=name):
                self.assertFalse(radar.run())
                self.assertIsNone(radar.image)
                self.assertNotEqual(radar.memory[0x6f24],0)

def live():
    def transport(path,headers):
        print('Native request:',headers['host'],path.split('?')[0],flush=True)
        request = urllib.request.Request('https://'+headers['host']+path,headers=headers)
        with urllib.request.urlopen(request,timeout=30) as reply:
            return reply.read(65536),reply.headers['Date']
    for country,name in ((0,'us'),(1,'ph')):
        radar = Radar(country,transport)
        okay = radar.run()
        print(name,'downloaded' if okay else 'unavailable','status',radar.memory[0x6f24],flush=True)
        if okay:
            target = ROOT/'build'/('native-'+name+'-radar.png')
            target.write_bytes(radar.image)
            print('Saved',target,'age',radar.word(0x6f2a),'seconds',flush=True)

if __name__ == '__main__':
    if '--live' in sys.argv:
        live()
    else:
        unittest.main()
