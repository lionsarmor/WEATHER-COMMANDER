#!/usr/bin/env python3
"""Native geocoding, exact IDs, URL escaping and transactional station changes."""
import copy
import json
import unittest
import urllib.parse
from py65.devices.mpu65c02 import MPU
from test_direct_inflate import Memory, ROOT

CITY = dict(id=5261457,name='Madison',country_code='US',admin1='Wisconsin',latitude=43.07305,longitude=-89.40123)

class Geo:
    def __init__(self):
        self.memory,self.fars,self.requests=Memory(),[],[]
        self.cpu=MPU(memory=self.memory)
        self.result=copy.deepcopy(CITY)
        self.weather_ok=True
        self.weather_calls=0
        for bank,module in ((12,'direct_geo'),(21,'direct_weather_decode'),(2,'direct_crypto')):
            self.memory[0]=bank
            code=(ROOT/'build'/(module+'_overlay.bin')).read_bytes()
            self.memory[0xa000:0xa000+len(code)]=code
            self.call(bank,0xa000)
        self.memory[0x9804]=2
    def word(self,addr): return self.memory[addr]+256*self.memory[addr+1]
    def exchange(self):
        mem=self.memory
        req=bytes(mem[0x8000:0x8000+self.word(0x6d70)]).decode()
        assert req.endswith('\r\n\r\n')
        line=req.split('\r\n')[0]
        method,path,version=line.split(' ')
        assert method=='GET' and version=='HTTP/1.0'
        self.requests.append(urllib.parse.urlsplit(path))
        result={'results':[self.result]} if self.requests[-1].path.endswith('search') else self.result
        raw=json.dumps(result).encode()
        mem[0x7000:0x7000+len(raw)]=raw
        mem[0x6d72:0x6d74]=len(raw).to_bytes(2,'little')
        mem[0x6d78]=1
    def call(self,bank,address):
        cpu,mem=self.cpu,self.memory
        mem[0]=bank;cpu.sp=255;cpu.stPushWord(0x2ff);cpu.pc=address
        for _ in range(10000000):
            if cpu.pc==0x300:
                assert mem[0]==bank and not self.fars
                return
            if cpu.pc==0xff6e:
                ret=cpu.stPopWord();target,dest=self.word(ret+1),mem[ret+3]
                if dest==20:
                    self.exchange();cpu.pc=ret+4
                elif dest==22:
                    if target==0xa003:
                        self.weather_calls+=1
                        mem[0x6a87]=int(self.weather_ok)
                        mem[0x6a84:0x6a86]=(1024 if self.weather_ok else 0).to_bytes(2,'little')
                        mem[0x6400:0x6800]=[0xab]*1024
                    else: assert target==0xa006
                    cpu.pc=ret+4
                else:
                    assert dest in (2,21)
                    self.fars.append((mem[0],ret+4));mem[0]=dest
                    cpu.stPushWord(0xfeff);cpu.pc=target
            elif cpu.pc==0xff00: mem[0],cpu.pc=self.fars.pop()
            else: cpu.step()
        raise AssertionError(f'Geocoder did not return: {mem[0]}:{cpu.pc:04x}')
    def run(self,operation,query='Madison, WI',city_id=CITY['id']):
        request=bytearray(64);request[:4]=b'WCC1';request[4]=operation
        text=query.encode();request[8:8+len(text)]=text
        request[56:60]=city_id.to_bytes(4,'little')
        request[60:62]=sum(request[:60]).to_bytes(2,'little')
        self.memory[0x6b00:0x6b40]=request
        self.memory[0x6000:0x6400]=[0x5a]*1024
        self.call(12,0xa003)
        assert bytes(self.memory[0x6000:0x6400])==b'\x5a'*1024
        assert bytes(self.memory[0x6400:0x6440])==request
        return self.memory[0x6440]

class GeoTests(unittest.TestCase):
    def test_search_escape_country_and_reply(self):
        geo=Geo();self.assertEqual(geo.run(1,query='Madison, WI&x=1'),1)
        query=urllib.parse.parse_qs(geo.requests[0].query)
        self.assertEqual(query['name'],['Madison, WI&x=1'])
        self.assertEqual(query['countryCode'],['US'])
        self.assertEqual(geo.memory[0x6441],1)
        self.assertEqual(bytes(geo.memory[0x6460:0x6464]),CITY['id'].to_bytes(4,'little'))
        self.assertEqual(bytes(geo.memory[0x6464:0x647f]).split(b'\0')[0],b'MADISON, WISCONSIN')
    def test_selection_commits_only_after_weather_success(self):
        geo=Geo();self.assertEqual(geo.run(2),2)
        self.assertEqual(geo.weather_calls,1)
        self.assertEqual(bytes(geo.memory[0x9890:0x989c]).split(b'\0')[0],b'43.07305')
        self.assertEqual(bytes(geo.memory[0x989c:0x98a8]).split(b'\0')[0],b'-89.40123')
        self.assertEqual(geo.memory[0x98e0],1)
        geo.weather_ok=False;before=bytes(geo.memory[0x9890:0x98e2]);geo.result['latitude']=42
        self.assertEqual(geo.run(2),4)
        self.assertEqual(bytes(geo.memory[0x9890:0x98e2]),before)
    def test_invalid_locations_never_change_station(self):
        for field,value in [('id',CITY['id']+1),('country_code','PH'),('latitude',90.1),('longitude',-180.1),('latitude',1e-7),('name','bad\nname')]:
            geo=Geo();geo.result[field]=value
            with self.subTest(field=field,value=value):
                self.assertEqual(geo.run(2),4)
                self.assertEqual(geo.weather_calls,0)
                self.assertEqual(geo.memory[0x98e0],0)
        geo=Geo();geo.memory[0x9804]=0
        self.assertEqual(geo.run(1),4);self.assertFalse(geo.requests)
    def test_ph_country_and_unsigned_id(self):
        geo=Geo();geo.memory[0x981e]=1;geo.result.update(country_code='PH',id=4000000000,name='Davao',latitude=7.07306,longitude=125.61278)
        self.assertEqual(geo.run(1),1)
        self.assertEqual(urllib.parse.parse_qs(geo.requests[-1].query)['countryCode'],['PH'])
        self.assertEqual(geo.run(2,city_id=4000000000),2)
        self.assertEqual(urllib.parse.parse_qs(geo.requests[-1].query)['id'],['4000000000'])
        self.assertEqual(geo.memory[0x98e1],1);self.assertEqual(geo.memory[0x98e0],0)

if __name__=='__main__': unittest.main()
