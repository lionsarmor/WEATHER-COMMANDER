#!/usr/bin/env python3
"""Compare native API decoding with known weather, including signed values."""
import copy,json,sys,unittest
from pathlib import Path
from py65.devices.mpu65c02 import MPU
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.weather import snapshot
from weather_fixture import weather_fixture
ROOT=Path(__file__).resolve().parents[1]

def fixture():
 data=weather_fixture()[0]
 data['current_units']={'time':'iso8601','temperature_2m':'°F','apparent_temperature':'°F','dew_point_2m':'°F','wind_speed_10m':'mp/h','visibility':'m','pressure_msl':'hPa'}
 data['daily_units']={'temperature_2m_max':'°F','temperature_2m_min':'°F'}
 data['hourly_units']={'time':'iso8601','temperature_2m':'°F'}
 data['hourly']={name:values[14:39] for name,values in data['hourly'].items()}
 return data

def decode(data,station=0):
 memory=[0]*65536;cpu=MPU(memory=memory)
 code=(ROOT/'build/direct_weather_decode_overlay.bin').read_bytes();memory[0xa000:0xa000+len(code)]=code
 def call(address):
  cpu.sp=255;cpu.stPushWord(0x2ff);cpu.pc=address
  for _ in range(10000000):
   if cpu.pc==0x300:return
   cpu.step()
  raise AssertionError('Native weather decoder did not return')
 call(0xa000)
 raw=json.dumps(data,separators=(',',':')).encode();assert len(raw)<=8192
 memory[0x7000:0x7000+len(raw)]=raw;memory[0x6d72:0x6d74]=len(raw).to_bytes(2,'little')
 memory[0x6eb0]=station;memory[0x63ff]=0xa5;memory[0x6800]=0x5a
 call(0xa003)
 assert memory[0x63ff]==0xa5 and memory[0x6800]==0x5a
 return bool(memory[0x6eb2]),bytes(memory[0x6400:0x6800])

class DirectWeatherTests(unittest.TestCase):
 def test_wrong_units_and_misaligned_hours_fail(self):
  for section,field,value in [('current_units','temperature_2m','°C'),('hourly_units','temperature_2m','°C'),('current_units','wind_speed_10m','km/h')]:
   data=fixture();data[section][field]=value
   with self.subTest(section=section,field=field):self.assertFalse(decode(data)[0])
  data=fixture();data['hourly']['time'][1]=data['hourly']['time'][0];self.assertFalse(decode(data)[0])
 def test_all_observations_daily_and_hourly_match(self):
  expected=snapshot(weather_fixture())
  for station in (0,9):
   valid,data=decode(fixture(),station);self.assertTrue(valid)
   self.assertEqual(data[32+station*32:64+station*32],expected[32:64])
   self.assertEqual(data[352+station*28:380+station*28],expected[352:380])
   self.assertEqual(data[632+station*24:656+station*24],expected[632:656])
 def test_negative_temperatures_and_night_icon(self):
  data=fixture();data['current']['temperature_2m']=-12.4;data['current']['is_day']=0;data['current']['weather_code']=0
  valid,out=decode(data);self.assertTrue(valid);self.assertEqual(out[32:34],bytes([244,0]))
 def test_high_visibility_does_not_overflow(self):
  data=fixture();data['current']['visibility']=100000.0
  valid,out=decode(data);self.assertTrue(valid);self.assertEqual(out[39],62)
 def test_missing_invalid_and_partial_observations_fail(self):
  for field,value in [('relative_humidity_2m',101),('temperature_2m',None),('weather_code',123),('wind_direction_10m',-1),('time','2026-13-12T01:00')]:
   data=fixture();data['current'][field]=value
   with self.subTest(field=field):self.assertFalse(decode(data)[0])
  data=fixture();data['hourly']['temperature_2m'].pop();self.assertFalse(decode(data)[0])
  data=fixture();del data['daily'];self.assertFalse(decode(data)[0])

if __name__=='__main__':unittest.main()
