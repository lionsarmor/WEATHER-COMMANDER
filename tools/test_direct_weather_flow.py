#!/usr/bin/env python3
"""Execute all ten native API decodes and verify cache/country transactions."""
import json
import unittest
import urllib.parse
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import Memory, ROOT
from test_direct_weather import fixture

class Weather:
    def __init__(self):
        self.memory,self.fars,self.requests=Memory(),[],[]
        self.cpu=MPU(memory=self.memory)
        self.minute=30;self.fail_at=None
        for bank,module in ((22,'direct_weather'),(21,'direct_weather_decode')):
            self.memory[0]=bank
            code=(ROOT/'build'/(module+'_overlay.bin')).read_bytes()
            self.memory[0xa000:0xa000+len(code)]=code
            self.call(bank,0xa000)
        self.memory[0x6000:0x6400]=[0x5a]*1024
    def word(self,addr): return self.memory[addr]+256*self.memory[addr+1]
    def exchange(self):
        m=self.memory
        req=bytes(m[0x8000:0x8000+self.word(0x6d70)]).decode()
        assert req.endswith('\r\n\r\n')
        method,path,version=req.split('\r\n')[0].split(' ')
        assert method=='GET' and version=='HTTP/1.0'
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
        assert query['forecast_hours']==['25'] and query['forecast_days']==['7']
        self.requests.append(query)
        m[0x6d78]=int(len(self.requests)!=self.fail_at)
        data=fixture();data['current']['temperature_2m']=60+len(self.requests)%10
        raw=json.dumps(data,separators=(',',':')).encode()
        assert len(raw)<=8192
        m[0x7000:0x7000+len(raw)]=raw
        m[0x6d72:0x6d74]=len(raw).to_bytes(2,'little')
    def call(self,bank,address):
        cpu,m=self.cpu,self.memory
        m[0]=bank;cpu.sp=255;cpu.stPushWord(0x2ff);cpu.pc=address
        for _ in range(80000000):
            if cpu.pc==0x300:
                assert m[0]==bank and not self.fars
                return
            if cpu.pc==0xff6e:
                ret=cpu.stPopWord();target,dest=self.word(ret+1),m[ret+3]
                if dest==20:self.exchange();cpu.pc=ret+4
                else:
                    assert dest==21
                    self.fars.append((m[0],ret+4));m[0]=dest;cpu.stPushWord(0xfeff);cpu.pc=target
            elif cpu.pc==0xff00:m[0],cpu.pc=self.fars.pop()
            elif cpu.pc==0xff50:
                m[2:10]=[126,9,10,14,self.minute,0,0,4];cpu.pc=cpu.stPopWord()+1
            else:cpu.step()
        raise AssertionError('Weather flow did not return')
    def fetch(self,country=0):
        self.memory[0x6eb1]=country;self.call(22,0xa003)
        assert bytes(self.memory[0x6000:0x6400])==b'\x5a'*1024
        if not self.memory[0x6a87]:return None
        assert self.word(0x6a84)==1024
        raw=bytes(self.memory[0x6400:0x6800]);assert raw[:6]==b'WCW2\2\x0a'
        assert int.from_bytes(raw[8:10],'little')==(sum(raw[6:8])+sum(raw[10:]))&65535
        return raw

class FlowTests(unittest.TestCase):
    def test_country_cache_and_personal_city(self):
        w=Weather();first=w.fetch();self.assertIsNotNone(first);self.assertEqual(len(w.requests),10)
        w.minute=44;self.assertEqual(w.fetch(),first);self.assertEqual(len(w.requests),10)
        m=w.memory;m[0x98e1]=1;m[0x98b8:0x98c4]=b'7.07306\0'.ljust(12,b'\0');m[0x98c4:0x98d0]=b'125.61278\0'.ljust(12,b'\0');m[0x98d0:0x98e0]=b'DAVAO HOME\0'.ljust(16,b'\0')
        ph=w.fetch(1);self.assertEqual(ph[15],1);self.assertEqual(ph[1000:1016].rstrip(b'\0'),b'DAVAO HOME')
        self.assertEqual(w.requests[10]['latitude'],['7.07306']);self.assertEqual(w.requests[10]['longitude'],['125.61278'])
        self.assertEqual(w.fetch(0),first);self.assertEqual(len(w.requests),20)
        w.minute=45;self.assertIsNotNone(w.fetch());self.assertEqual(len(w.requests),30)
    def test_partial_country_never_becomes_cache(self):
        w=Weather();w.fail_at=5;self.assertIsNone(w.fetch());self.assertEqual(len(w.requests),5)
        w.fail_at=None;self.assertIsNotNone(w.fetch());self.assertEqual(len(w.requests),15)

def live():
    import urllib.request
    class Live(Weather):
        def exchange(self):
            m=self.memory
            request=bytes(m[0x8000:0x8000+self.word(0x6d70)]).decode()
            path=request.split(' ',2)[1]
            print('Native weather request',len(self.requests)+1,flush=True)
            with urllib.request.urlopen('https://api.open-meteo.com'+path,timeout=30) as response:
                raw=response.read(8193)
            assert len(raw)<=8192
            self.requests.append(path)
            m[0x7000:0x7000+len(raw)]=raw
            m[0x6d72:0x6d74]=len(raw).to_bytes(2,'little')
            m[0x6d78]=1
            (ROOT/'build/native-weather-last.json').write_bytes(raw)
    weather=Live()
    for country in (0,1):
        raw=weather.fetch(country)
        assert raw is not None, f'Country {country} failed native weather decode'
        (ROOT/'build'/('native-weather-'+('ph' if country else 'us')+'.bin')).write_bytes(raw)
        print('PASS: native ten-city direct weather',country,flush=True)

if __name__=='__main__':
    import sys
    if '--live' in sys.argv:live()
    else:unittest.main()
