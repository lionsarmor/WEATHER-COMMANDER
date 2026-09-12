"""Local file/HTTP bridge. Run: python -m backend.server --output dist/sdcard"""
import argparse, json, os, tempfile, threading, time, socket, math, urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .weather import CITIES,fetch_weather,snapshot
from .cities import search,reply,validate_request
from .radar import fetch_radar,fresh,checksum
from .pagasa import fetch_philippines
from .countries import PROFILES,WIRE_IDS

def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  temporary=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
 try:os.replace(temporary,path)
 finally:temporary.unlink(missing_ok=True)

class Bridge:
 def __init__(self,output):
  self.output=Path(output);self.weather=None;self.fetched=None;self.last_weather=0;self.last_radar=0
  self.healthy=False;self.radar=None;self.error=None;self.stop=threading.Event()
  self.lock=threading.RLock();self.city_lock=threading.Lock();self.radar_lock=threading.Lock();self.cities=list(CITIES)
  self.candidates={};self.city_request=None;self.city_reply=None
  self.country='US';self.personal={}
  def location(saved):
   name=saved['name'];lat=float(saved['latitude']);lon=float(saved['longitude'])
   if not isinstance(name,str) or not 1<=len(name)<=14 or any(not 32<=ord(c)<=126 for c in name):raise ValueError('City name')
   if not math.isfinite(lat) or not -90<=lat<=90 or not math.isfinite(lon) or not -180<=lon<=180:raise ValueError('City coordinates')
   return (name,lat,lon)
  try:
   config=json.loads((self.output/'locations.json').read_text())
   country=config['country']
   if country not in PROFILES:raise ValueError('Country')
   personal={code:location(value) for code,value in config['personal'].items() if code in PROFILES}
   self.country=country;self.personal=personal
  except (OSError,ValueError,KeyError,TypeError,AttributeError):
   try:self.personal['US']=location(json.loads((self.output/'city.json').read_text()))
   except (OSError,ValueError,KeyError,TypeError):pass
  self.cities=self.profile(self.country)
 def profile(self,country):
  cities=list(PROFILES[country])
  if country in self.personal:cities[0]=self.personal[country]
  return cities
 def save_locations(self,country,personal):
  value={'country':country,'personal':{code:dict(zip(('name','latitude','longitude'),city)) for code,city in personal.items()}}
  atomic(self.output/'locations.json',json.dumps(value).encode())
 def weather_bytes(self):
  with self.lock:
   if self.weather is None:return None
   return snapshot(self.weather,self.fetched,self.healthy,fresh(self.radar,WIRE_IDS[self.country]),self.cities,WIRE_IDS[self.country])
 def city_message(self,request):
  query,ident=validate_request(request)
  with self.city_lock:
   if request==self.city_request:return self.city_reply
   try:
    if request[4]==1:
     matches=search(query);self.candidates={m['id']:m for m in matches}
     result=reply(request,1 if matches else 3,'CHOOSE A MATCH' if matches else 'NO MATCH / TRY CITY, STATE',matches)
    else:
     country=self.country;personal=dict(self.personal)
     if request[4]==3:
      if query not in PROFILES:raise ValueError('Unknown country')
      country=query;cities=self.profile(country)
     else:
      if ident not in self.candidates:
       result=reply(request,3,'SEARCH AGAIN TO CHOOSE A CITY')
       self.city_request=request;self.city_reply=result
       return result
      selected=self.candidates[ident]
      cities=[(selected['name'],selected['latitude'],selected['longitude'])]+list(PROFILES[country][1:])
      personal[country]=cities[0]
     data=fetch_weather(cities);fetched=datetime.now().astimezone()
     # Commit country, city labels and observations together after validation.
     with self.lock:
      payload=snapshot(data,fetched,True,fresh(self.radar,WIRE_IDS[country]),cities,WIRE_IDS[country])
      self.save_locations(country,personal)
      atomic(self.output/'WCDATA.BIN',payload)
      self.country=country;self.personal=personal
      self.cities=cities;self.weather=data;self.fetched=fetched
      self.healthy=True;self.error=None;self.last_weather=time.monotonic()
      if self.radar and self.radar[5]!=WIRE_IDS[country]:
       self.radar=None;self.last_radar=0
       (self.output/'WCRLIVE.BIN').unlink(missing_ok=True)
      if request[4]==3:self.candidates={}
     result=reply(request,2,'COUNTRY READY' if request[4]==3 else 'CITY ADDED / OPENING YOUR LIST')
   except Exception as exc:
    result=reply(request,4,'LOOKUP FAILED / PLEASE RETRY')
    print(f'City lookup unavailable: {type(exc).__name__}',flush=True)
   self.city_request=request;self.city_reply=result
   return result
 def city_poll(self):
  try:
   with (self.output/'WCQUERY.BIN').open('rb') as f:request=f.read(65)
   validate_request(request)
  except (OSError,ValueError,UnicodeError):return
  if request==self.city_request:return
  result=self.city_message(request)
  atomic(self.output/'WCCITIES.BIN',result)
 def city_loop(self):
  while not self.stop.is_set():
   try:self.city_poll()
   except Exception as exc:print(f'City request failed: {type(exc).__name__}',flush=True)
   self.stop.wait(.5)
 def update_radar(self):
  # A cold HTTP request can populate radar immediately; concurrent requests share it.
  with self.radar_lock:
   now=time.monotonic()
   with self.lock:
    radar_country=self.country
    if now-self.last_radar<300 and fresh(self.radar,WIRE_IDS[radar_country]):return
   try:
    radar=fetch_radar() if radar_country=='US' else fetch_philippines()
    if not fresh(radar,WIRE_IDS[radar_country]):raise ValueError('Radar observation is stale')
    with self.lock:
     if self.country==radar_country:
      self.radar=radar;self.last_radar=now;atomic(self.output/'WCRLIVE.BIN',radar)
   except Exception as exc:
    with self.lock:
     if self.country==radar_country and self.radar:
      old=bytearray(self.radar);old[14]=1;old[12:14]=checksum(old).to_bytes(2,'little')
      self.radar=bytes(old);atomic(self.output/'WCRLIVE.BIN',self.radar)
    print(f'Radar unavailable: {type(exc).__name__}',flush=True)
 def update(self):
  now=time.monotonic()
  if self.weather is None or now-self.last_weather>=600:
   try:
    with self.lock:cities=list(self.cities);country=self.country
    data=fetch_weather(cities);fetched=datetime.now().astimezone()
    with self.lock:
     if cities==self.cities and country==self.country:
      snapshot(data,fetched,cities=cities,country=WIRE_IDS[country])
      self.weather=data;self.fetched=fetched;self.healthy=True;self.error=None;self.last_weather=now
   except Exception as exc:
    with self.lock:
     if cities==self.cities and country==self.country:self.healthy=False;self.error=type(exc).__name__
    print(f'Weather unavailable: {type(exc).__name__}',flush=True)
    # A fresh launch without Internet must not leave yesterday's file marked online.
    cached=self.output/'WCDATA.BIN'
    with self.lock:
     if self.weather is None and cached.exists():
      raw=bytearray(cached.read_bytes())
      if len(raw)==1024 and raw[:4]==b'WCW2':
       raw[6]=0;raw[8:10]=((sum(raw[6:8])+sum(raw[10:]))&65535).to_bytes(2,'little');atomic(cached,raw)
  self.update_radar()
  with self.lock:
   if self.weather:atomic(self.output/'WCDATA.BIN',self.weather_bytes())
  atomic(self.output/'bridge-status.json',json.dumps({'country':self.country,'online':self.healthy,'weather_fetched':self.fetched.isoformat() if self.fetched else None,'radar':fresh(self.radar,WIRE_IDS[self.country]),'error':self.error}).encode())
 def loop(self):
  while not self.stop.is_set():
   try:self.update()
   except Exception as exc:print(f'Bridge update failed: {type(exc).__name__}',flush=True)
   self.stop.wait(60)

def handler(bridge):
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   if self.path=='/health':body=b'WEATHER COMMANDER BRIDGE';kind='text/plain'
   elif self.path=='/x16/weather.hex':
    if not bridge.weather:self.send_error(503,'Weather unavailable');return
    body=b'WC2:'+bridge.weather_bytes().hex().upper().encode()+b'\r\n';kind='text/plain'
   elif self.path.startswith('/x16/city.hex?'):
    try:
     value=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)['request'][0]
     if len(value)!=128:raise ValueError('Request length')
     body=b'WC2:'+bridge.city_message(bytes.fromhex(value)).hex().upper().encode()+b'\r\n';kind='text/plain'
    except (ValueError,KeyError,UnicodeError):self.send_error(400,'Invalid city request');return
   elif self.path=='/x16/radar.hex':
    bridge.update_radar()
    with bridge.lock:radar=bridge.radar;country=bridge.country
    if not fresh(radar,WIRE_IDS[country]):self.send_error(503,'Fresh radar unavailable');return
    body=b'WC2:'+radar.hex().upper().encode()+b'\r\n';kind='text/plain'
   else:self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 return Handler

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('dist/sdcard'))
 parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--port',type=int,default=8767);parser.add_argument('--once',action='store_true')
 args=parser.parse_args();bridge=Bridge(args.output)
 if args.once:bridge.update();return
 server=ThreadingHTTPServer((args.bind,args.port),handler(bridge))
 thread=threading.Thread(target=bridge.loop,daemon=True);thread.start()
 city_thread=threading.Thread(target=bridge.city_loop,daemon=True);city_thread.start()
 print(f'Weather bridge listening on {args.bind}:{args.port}',flush=True)
 if args.bind=='0.0.0.0':
  try:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
    probe.connect(('8.8.8.8',80));address=probe.getsockname()[0]
   print(f'On your X16, enter this weather computer address: {address}:{args.port}',flush=True)
  except OSError:print('On your X16, enter this computer\'s LAN IP address.',flush=True)
  print('Keep this window open while using your weather station.',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:bridge.stop.set();server.server_close()
if __name__=='__main__':main()
