#!/usr/bin/env python3
"""City lookup, persistence and preservation of the nine standard stations."""
import sys, tempfile, unittest, threading, urllib.request, urllib.parse, json
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.cities import search,validate_request
from backend.server import Bridge,handler
from backend.weather import CITIES
from backend.countries import PHILIPPINES
from weather_fixture import weather_fixture
from radar_fixture import radar_fixture

MATCH={'id':5261457,'name':'MADISON','label':'MADISON, WISCONSIN','latitude':43.0731,'longitude':-89.4012}
def request(operation=1,serial=1,query='MADISON, WI',ident=0):
 out=bytearray(64);out[:4]=b'WCC1';out[4]=operation;out[5]=serial
 out[8:56]=query.encode().ljust(48,b'\0');out[56:60]=ident.to_bytes(4,'little')
 out[60:62]=sum(out[:60]).to_bytes(2,'little')
 return bytes(out)

class CityTests(unittest.TestCase):
 def test_country_switch_restores_personal_city_and_persists_profile(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.search',return_value=[MATCH]),patch('backend.server.fetch_weather',return_value=weather_fixture()) as fetch:
    bridge.city_message(request());bridge.city_message(request(2,2,ident=MATCH['id']))
    bridge.radar=b'old US radar';(Path(folder)/'WCRLIVE.BIN').write_bytes(bridge.radar)
    result=bridge.city_message(request(3,3,query='PH'))
    self.assertEqual(result[64],2);self.assertEqual(fetch.call_args.args[0],PHILIPPINES)
    self.assertEqual(bridge.country,'PH');self.assertEqual(bridge.weather_bytes()[15],1)
    self.assertEqual(bridge.weather_bytes()[7],0);self.assertIsNone(bridge.radar)
    self.assertFalse((Path(folder)/'WCRLIVE.BIN').exists())
    self.assertEqual(Bridge(folder).cities,PHILIPPINES)
    self.assertEqual(Bridge(folder).country,'PH')
    result=bridge.city_message(request(3,4,query='US'))
    self.assertEqual(result[64],2);self.assertEqual(bridge.cities[0][0],'MADISON')
    self.assertEqual(bridge.weather_bytes()[15],0)
    self.assertEqual(Bridge(folder).cities,bridge.cities)
 def test_country_failure_retains_previous_weather_and_profile(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.fetch_weather',return_value=weather_fixture()):bridge.city_message(request(3,1,query='PH'))
   old=bridge.weather_bytes();config=(Path(folder)/'locations.json').read_bytes()
   with patch('backend.server.fetch_weather',side_effect=OSError):
    self.assertEqual(bridge.city_message(request(3,2,query='US'))[64],4)
   self.assertEqual(bridge.country,'PH');self.assertEqual(bridge.weather_bytes(),old)
   self.assertEqual((Path(folder)/'locations.json').read_bytes(),config)
   with patch('backend.server.fetch_weather') as fetch:
    self.assertEqual(bridge.city_message(request(3,3,query='XX'))[64],4);fetch.assert_not_called()
 def test_philippines_refresh_never_downloads_us_radar(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.fetch_weather',return_value=weather_fixture()),patch('backend.server.fetch_radar') as radar,patch('backend.server.fetch_philippines',return_value=radar_fixture(1)) as ph:
    bridge.city_message(request(3,1,query='PH'));bridge.last_weather=0;bridge.update()
    radar.assert_not_called();ph.assert_called_once()
    self.assertEqual(bridge.weather_bytes()[7],1)
   self.assertEqual(bridge.weather_bytes()[15],1)
 def test_geocoder_passes_qualifier_and_returns_bounded_labels(self):
  row={'id':5261457,'name':'Madison','admin1':'Wisconsin','latitude':43.0731,'longitude':-89.4012}
  with patch('backend.cities.fetch_json',return_value={'results':[row]}) as fetch:
   self.assertEqual(search('MADISON, WI'),[MATCH])
  self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)['name'],['MADISON, WI'])
 def test_add_persists_name_weather_and_preserves_other_cities(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.search',return_value=[MATCH]):found=bridge.city_message(request())
   self.assertEqual(found[:64],request());self.assertEqual(found[64:66],b'\x01\x01')
   self.assertEqual(int.from_bytes(found[96:100],'little'),MATCH['id'])
   with patch('backend.server.fetch_weather',return_value=weather_fixture()) as fetch:
    added=bridge.city_message(request(2,2,ident=MATCH['id']))
   self.assertEqual(added[64],2);self.assertEqual(fetch.call_args.args[0][0],('MADISON',43.0731,-89.4012))
   self.assertEqual(bridge.cities[1:],CITIES[1:])
   wire=(Path(folder)/'WCDATA.BIN').read_bytes()
   self.assertEqual(wire[1000:1016],b'MADISON'.ljust(16,b'\0'))
   self.assertEqual(wire,bridge.weather_bytes())
   self.assertEqual(Bridge(folder).cities,bridge.cities)
 def test_failed_weather_never_changes_saved_city_or_snapshot(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder);cache=Path(folder)/'WCDATA.BIN';cache.write_bytes(b'previous snapshot')
   with patch('backend.server.search',return_value=[MATCH]):bridge.city_message(request())
   bad=weather_fixture();bad[0]['current']['temperature_2m']=None
   with patch('backend.server.fetch_weather',return_value=bad):result=bridge.city_message(request(2,2,ident=MATCH['id']))
   self.assertEqual(result[64],4);self.assertEqual(bridge.cities,CITIES)
   self.assertEqual(cache.read_bytes(),b'previous snapshot');self.assertFalse((Path(folder)/'city.json').exists())
 def test_unknown_id_and_no_matches_do_not_change_weather(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder)
   with patch('backend.server.search',return_value=[]):self.assertEqual(bridge.city_message(request())[64],3)
   with patch('backend.server.fetch_weather') as fetch:
    self.assertEqual(bridge.city_message(request(2,2,ident=999))[64],3);fetch.assert_not_called()
 def test_hostfs_partial_request_retry_and_echo(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder);path=Path(folder)/'WCQUERY.BIN';path.write_bytes(request()[:20])
   bridge.city_poll();self.assertFalse((Path(folder)/'WCCITIES.BIN').exists())
   path.write_bytes(request())
   with patch('backend.server.search',side_effect=OSError):bridge.city_poll()
   self.assertEqual((Path(folder)/'WCCITIES.BIN').read_bytes()[64],4)
   path.write_bytes(request(serial=2))
   with patch('backend.server.search',return_value=[MATCH]):bridge.city_poll()
   raw=(Path(folder)/'WCCITIES.BIN').read_bytes()
   self.assertEqual(raw[:64],request(serial=2));self.assertEqual(raw[64],1)
 def test_bad_requests_and_saved_coordinates_are_rejected(self):
  bad=bytearray(request());bad[12]^=1
  with self.assertRaises(ValueError):validate_request(bad)
  with tempfile.TemporaryDirectory() as folder:
   (Path(folder)/'city.json').write_text(json.dumps({'name':'BAD','latitude':999,'longitude':0}))
   self.assertEqual(Bridge(folder).cities,CITIES)
 def test_http_uses_same_city_protocol(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder);server=ThreadingHTTPServer(('127.0.0.1',0),handler(bridge))
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    with patch('backend.server.search',return_value=[MATCH]):
     with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/x16/city.hex?request='+request().hex()) as response:
      raw=bytes.fromhex(response.read()[4:].decode())
    self.assertEqual(raw[:64],request());self.assertEqual(raw[64:66],b'\x01\x01')
   finally:server.shutdown();server.server_close();thread.join()
 def test_inflight_refresh_cannot_overwrite_added_city(self):
  with tempfile.TemporaryDirectory() as folder:
   bridge=Bridge(folder);started=threading.Event();release=threading.Event()
   bridge.last_radar=__import__('time').monotonic()
   def fetch(cities):
    if cities[0][0]==CITIES[0][0]:
     started.set()
     if not release.wait(3):raise TimeoutError('Test refresh did not resume')
    return weather_fixture()
   with patch('backend.server.search',return_value=[MATCH]),patch('backend.server.fetch_weather',side_effect=fetch),patch('backend.server.fetch_radar',return_value=radar_fixture()):
    bridge.city_message(request())
    worker=threading.Thread(target=bridge.update);worker.start()
    try:
     self.assertTrue(started.wait(2))
     self.assertEqual(bridge.city_message(request(2,2,ident=MATCH['id']))[64],2)
    finally:release.set();worker.join(timeout=3)
   self.assertFalse(worker.is_alive());self.assertEqual(bridge.cities[0][0],'MADISON')
   self.assertEqual((Path(folder)/'WCDATA.BIN').read_bytes()[1000:1016],b'MADISON'.ljust(16,b'\0'))
if __name__=='__main__':unittest.main()
