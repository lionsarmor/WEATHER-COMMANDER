#!/usr/bin/env python3
"""Weather adapter, radar budgets, bridge routes and offline preservation."""
import sys,unittest,copy,tempfile,threading,urllib.request
from pathlib import Path
from datetime import datetime
from io import BytesIO
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.weather import snapshot,condition
from backend.radar import encode,SIZE,fetch_radar,LEVELS,checksum,fresh
from backend.geometry import project,unproject,pixel
from backend.server import Bridge,handler
from weather_fixture import weather_fixture
from radar_fixture import radar_fixture

class WeatherTests(unittest.TestCase):
 def setUp(self):
  # Timer-reset tests must not depend on the test machine's uptime.
  clock=patch('backend.server.time.monotonic',return_value=10000)
  clock.start();self.addCleanup(clock.stop)
 def test_first_fetch_runs_immediately_after_computer_reboot(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.time.monotonic',return_value=12),patch('backend.server.fetch_weather',return_value=weather_fixture()) as fetch,patch.object(bridge,'update_radar'):
    bridge.update()
    fetch.assert_called_once()
    self.assertTrue(bridge.healthy)
    self.assertEqual((Path(folder)/'WCDATA.BIN').read_bytes()[6],1)
    bridge.update()
    fetch.assert_called_once()
 def test_demo_and_corrupt_headers_are_never_live(self):
  for country in (0,1):
   self.assertTrue(fresh(radar_fixture(country),country))
   self.assertFalse(fresh(radar_fixture(country,demo=True),country))
   bad=bytearray(radar_fixture(country));bad[5]=1-country
   self.assertFalse(fresh(bad))
 def test_offline_transition_marks_radar_and_recovers(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.fetch_radar',return_value=radar_fixture()):bridge.update_radar()
   self.assertTrue(fresh(bridge.radar));bridge.last_radar=0
   with patch('backend.server.fetch_radar',side_effect=OSError):bridge.update_radar()
   self.assertFalse(fresh(bridge.radar));self.assertEqual(bridge.radar[14],1)
   self.assertEqual((Path(folder)/'WCRLIVE.BIN').read_bytes(),bridge.radar)
   with patch('backend.server.fetch_radar',return_value=radar_fixture()):bridge.update_radar()
   self.assertTrue(fresh(bridge.radar))
 def test_philippine_numeric_rain_is_georeferenced(self):
  import math
  from PIL import ImageDraw
  from backend.pagasa import encode_rain
  bounds=[115,4,130,23];raw=Image.new('RGBA',(750,1024))
  merc=lambda v:math.log(math.tan(math.pi/4+math.radians(v)/2))
  x=round((121-115)/15*750);y=round((merc(23)-merc(15))/(merc(23)-merc(4))*1024)
  ImageDraw.Draw(raw).rectangle((x-8,y-8,x+8,y+8),fill=(255,0,0,255))
  buf=BytesIO();raw.save(buf,format='PNG')
  meta={'bounds':bounds,'scale':{'mode':'rain','unit':'mm/hr','sqrt':True,'max':80}}
  out=encode_rain(buf.getvalue(),meta,datetime.now().astimezone())
  self.assertTrue(fresh(out,1));self.assertLessEqual(out[4],207)
  # 121 E / 15 N falls at (139,81) on the native country map.
  def sample(px,py):
   tile=int.from_bytes(out[6640+(py//8*42+px//8)*2:6642+(py//8*42+px//8)*2],'little')&1023
   value=out[16+(tile-257)*32+py%8*4+px%8//2]
   return value>>(4 if px%2==0 else 0)&15
  self.assertEqual(sample(139,81),15);self.assertEqual(sample(20,20),2)
  # The styled map cannot paint terrain as a rain intensity.
  from backend.maps import philippines
  self.assertFalse(set(philippines().getdata()) & set(LEVELS))
  empty=Image.new('RGBA',(750,1024));buf=BytesIO();empty.save(buf,format='PNG')
  out=encode_rain(buf.getvalue(),meta,datetime.now().astimezone())
  self.assertFalse({sample(x,y) for y in range(224) for x in range(336)} & set(LEVELS))
  meta['scale']['max']=100
  with self.assertRaises(ValueError):encode_rain(buf.getvalue(),meta,datetime.now())
 def test_complete_snapshot(self):
  data=weather_fixture();out=snapshot(data,datetime(2026,9,10,14,30))
  self.assertEqual(len(out),1024);self.assertEqual(out[:6],b'WCW2\x02\x0a')
  self.assertEqual(int.from_bytes(out[8:10],'little'),(sum(out[6:8])+sum(out[10:]))&65535)
  self.assertEqual(out[32:38],bytes([70,2,48,8,50,81]))
  self.assertEqual(out[48:50],(2998).to_bytes(2,'little'))
  self.assertEqual(out[50:54],bytes([6,25,19,8]))
  self.assertEqual(out[352:356],bytes([80,50,2,10]))
  self.assertEqual(out[632:635],bytes([64,2,14]))
 def test_missing_values_fail_instead_of_inventing(self):
  data=weather_fixture();data[1]['current']['visibility']=None
  with self.assertRaises(TypeError):snapshot(data)
  self.assertEqual([condition(c) for c in (0,3,61,71,95,45)],[1,2,3,4,5,6])
  with self.assertRaises(ValueError):condition(123)
 def test_radar_is_bounded(self):
  image=Image.new('RGB',(600,392),'navy');buf=BytesIO();image.save(buf,format='GIF')
  out=encode(buf.getvalue(),datetime(2026,9,10,14,30));self.assertEqual(len(out),SIZE)
  self.assertLessEqual(out[4],207)
  self.assertEqual(int.from_bytes(out[12:14],'little'),checksum(out))
  ids=[int.from_bytes(out[i:i+2],'little') for i in range(6640,SIZE,2)]
  self.assertTrue(all(257<=(i&1023)<257+out[4] and i>>12==15 for i in ids))
 def test_radar_is_georeferenced_and_transparent(self):
  from PIL import ImageDraw
  raw=Image.new('RGBA',(756,360),(0,0,0,0));draw=ImageDraw.Draw(raw)
  lon,lat=-87.63,41.88
  x=int((lon+128)/63*756);y=int((52-lat)/30*360)
  draw.rectangle((x-5,y-5,x+5,y+5),fill=(20,210,40,255))
  buf=BytesIO();raw.save(buf,format='PNG');out=encode(buf.getvalue())
  def sample(x,y):
   x=int(x);y=int(y);pos=6640+(y//8*42+x//8)*2
   tile=(int.from_bytes(out[pos:pos+2],'little')&1023)-257
   data=out[16+tile*32+y%8*4+x%8//2]
   return (data>>(4 if x%2==0 else 0))&15
  self.assertEqual(sample(*pixel(lon,lat)),8)
  self.assertEqual(sample(*pixel(-122.33,47.61)),0)
  for point in [(-122.33,47.61),(-87.63,41.88),(-80.19,25.76)]:
   result=unproject(*project(*point))
   self.assertAlmostEqual(result[0],point[0],places=8);self.assertAlmostEqual(result[1],point[1],places=8)
  self.assertEqual(out[:4],b'WCR4')
 def test_radar_locks_conus_raster_and_preserves_observation_time(self):
  import json
  stamp=datetime(2026,9,11,14,30).astimezone();calls=[]
  image=Image.new('RGBA',(756,360),(0,0,0,0));buf=BytesIO();image.save(buf,format='PNG')
  def reply(path,params,limit):
   calls.append((path,params))
   if path=='/query':return json.dumps({'features':[{'attributes':{'objectid':123,'idp_validtime':int(stamp.timestamp()*1000)}}]}).encode()
   return buf.getvalue()
  with patch('backend.radar.request',side_effect=reply):out=fetch_radar()
  self.assertEqual(calls[0][1]['where'],"idp_subset='CONUS'")
  self.assertEqual(json.loads(calls[1][1]['mosaicRule'])['lockRasterIds'],[123])
  self.assertEqual(out[6:11],bytes([126,9,11,14,30]))
 def test_bridge_preserves_cached_data_and_marks_failure(self):
  with tempfile.TemporaryDirectory() as d:
   b=Bridge(d)
   with patch('backend.server.fetch_weather',return_value=weather_fixture()),patch('backend.server.fetch_radar',side_effect=OSError):b.update()
   original=b.fetched;b.last_weather=0
   with patch('backend.server.fetch_weather',side_effect=OSError),patch('backend.server.fetch_radar',side_effect=OSError):b.update()
   self.assertEqual(b.fetched,original);self.assertFalse(b.healthy)
   self.assertEqual((Path(d)/'WCDATA.BIN').read_bytes()[6],0)
 def test_http_endpoint(self):
  with tempfile.TemporaryDirectory() as d:
   b=Bridge(d);b.weather=weather_fixture();b.fetched=datetime(2026,9,10,14,30);b.healthy=True
   server=ThreadingHTTPServer(('127.0.0.1',0),handler(b));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/x16/weather.hex') as r:body=r.read()
    self.assertTrue(body.startswith(b'WC2:'));self.assertEqual(len(bytes.fromhex(body[4:].decode())),1024)
    with patch('backend.server.fetch_radar',return_value=radar_fixture()):
     with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/x16/radar.hex') as r:radar=bytes.fromhex(r.read()[4:].decode())
    self.assertTrue(fresh(radar,0))
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
