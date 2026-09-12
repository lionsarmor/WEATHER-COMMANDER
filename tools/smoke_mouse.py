#!/usr/bin/env python3
"""r49 pointer probe: real ROM positioning, injected button edges, real event loop.

All changes are in a temporary test PRG. No physical mouse/card is required.
The fixture is deterministic weather, explicitly generated for this test only.
The bridge-address screenshot injects the post-join state; hardware joining
is separately covered by the compiled UART simulation, not by this ROM probe.
"""
from pathlib import Path
import os, subprocess, tempfile, time, sys, threading
from unittest.mock import patch
from datetime import datetime
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.weather import snapshot
from weather_fixture import weather_fixture
from backend.server import Bridge
from test_cities import MATCH
from radar_fixture import radar_fixture
from build import TOOLS
ENV=dict(os.environ,SDL_VIDEODRIVER='dummy',PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
# Name, click tip X/Y, expected page. This exercises every view using only clicks.
steps=[('home',142,340,0),('national',60,116,1),('regional',60,140,2),
 ('local',60,164,3),('radar',60,188,4),('forecast',60,212,5),
 ('hourly',420,120,5),('daily',210,120,5),('cities',60,236,6),
 ('next-city',420,320,6),('city-report',300,292,3),('forecast-button',300,320,5),
 ('settings',60,260,7),('celsius',200,164,7),('wifi',200,120,10),
 ('modem',200,280,10),('hidden-network',200,352,10),
 ('ssid',200,192,10),('password',200,240,10),('network-back',110,444,10),
 ('computer-ready',200,264,10),('save-weather',450,444,0),('wifi-again',520,30,10),
 ('bridge',200,256,10),('bridge-back',110,444,10),('back',560,80,7),
 ('about',60,284,8),('help',300,320,9),('footer-cities',160,460,6),
 ('footer-forecast',270,460,5),('footer-radar',370,460,4),
 ('footer-settings',480,460,7),('home-again',60,92,0),
 ('add-city',400,340,11),('city-query',220,140,11),('city-search',220,170,11),
 ('city-match',240,228,6),('city-added',142,340,6),('city-home',60,92,0),
 ('country-ph',390,240,1),('ph-national',60,116,1),('ph-davao',416,264,3),
 ('ph-regional',60,140,2),('ph-radar',60,188,4),('ph-radar-connect',380,312,10),('ph-get-live',200,180,10),('ph-wifi-close',560,80,7),('ph-radar-live',60,188,4),('ph-home',60,92,0),
 ('country-us',220,240,1),('us-home',60,92,0)]
scene_start=len(steps)
steps += [(f'scene-{theme}-{phase}',550,380,0) for phase in range(4) for theme in range(7)]
steps += [('top-left',0,0,0),('edge',639,479,0),('footer-exit',580,460,0)]
n=len(steps)
match_step=next(i for i,s in enumerate(steps) if s[0]=='city-match')
async_steps=[i for i,s in enumerate(steps) if s[0] in ('city-match','country-ph','country-us')]
async_condition=' and '.join(f'smoke_step!={i}' for i in async_steps)
query_step=next(i for i,s in enumerate(steps) if s[0]=='city-query')
city_keys='\n'.join(f'                    key={ord(c)}\n                    handle_key()' for c in 'MADISON, WI')
source=(ROOT/'src/main.p8').read_text()
source=source.replace('    uword now',f'''    uword smoke_frames=0
    ubyte smoke_step=0
    uword[{n}] smoke_x={[s[1] for s in steps]}
    uword[{n}] smoke_y={[s[2] for s in steps]}
    ubyte[{n}] smoke_pages={[s[3] for s in steps]}
    ubyte[{n}] smoke_duration={[180 if s[0] in ('city-search','city-match','country-ph','country-us') else 30 for s in steps]}
    ubyte[{n}] smoke_hours={[10]*scene_start+[h for h in (6,10,18,22) for _ in range(7)]+[22,22,22]}
    uword now''',1)
source=source.replace('    sub start() {','''    sub smoke_radar_file(str filename) {
        uword length=0
        if diskio.f_open(filename) {
            length=diskio.f_read($7000,8992)
            diskio.f_close()
        }
        if length==8992 and diskio.f_open_w(iso:"@:WCRLIVE.BIN") {
            void diskio.f_write($7000,8992)
            diskio.f_close_w()
        }
    }
    sub start() {''',1)
source=source.replace('        hour=msb(dh)','        hour=smoke_hours[smoke_step]')
source=source.replace('            buttons,mx,my,wheel=cx16.mouse_pos()',f'''            if smoke_frames==0 {{
                if smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='computer-ready')} smoke_radar_file(iso:"WCRTEST.BIN")
                if smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='ph-get-live')} smoke_radar_file(iso:"WCRTPH.BIN")
                if smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='bridge')} {{
                    state.wifi_step=3
                    state.wifi_host=false
                    network_mailbox.connection=3
                    redraw()
                }}
                cx16.mouse_set_pos(smoke_x[smoke_step],smoke_y[smoke_step])
                if smoke_step=={query_step} {{
{city_keys}
                }}
                if smoke_step>={scene_start} and smoke_step<{scene_start+28} {{
                    state.hour=smoke_hours[smoke_step]
                    state.scenery=(smoke_step-{scene_start}+6) % 7
                }}
            }}
            buttons,mx,my,wheel=cx16.mouse_pos()
            if smoke_frames==0 buttons=1
            else buttons=0''',1)
source=source.replace('            service_timers()',f'''            service_timers()
            if state.page!=smoke_pages[smoke_step] and (({async_condition}) or smoke_frames>=179) {{
                txt.print(iso:"MOUSE ROUTE FAILED\\r\\n")
                running=false
            }}
            smoke_frames++
            if smoke_frames==smoke_duration[smoke_step] or not running {{
                if smoke_step=={match_step} and (@($63e8)!=77 or @($63e9)!=65 or state.city!=0) {{
                    txt.print(iso:"CITY ADD FAILED\\r\\n")
                    running=false
                }}
                if smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='country-ph')} and (state.country!=1 or @($63e8)!=77 or state.radar_ready) {{
                    txt.print(iso:"COUNTRY SWITCH FAILED\\r\\n")
                    running=false
                }}
                if smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='country-us')} and (state.country!=0 or @($63ea)!=68) {{
                    txt.print(iso:"COUNTRY RESTORE FAILED\\r\\n")
                    running=false
                }}
                if (smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='computer-ready')} or smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='ph-get-live')}) and (not state.radar_ready or state.radar_demo) {{
                    txt.print(iso:"LIVE RADAR TRANSITION FAILED\\r\\n")
                    running=false
                }}
                if (smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='radar')} or smoke_step=={next(i for i,s in enumerate(steps) if s[0]=='ph-radar')}) and (state.radar_ready or not state.radar_demo) {{
                    txt.print(iso:"DEMO RADAR LABEL FAILED\\r\\n")
                    running=false
                }}
                @($9fb5)=1
                smoke_frames=0
                smoke_step++
                if smoke_step=={n} running=false
            }}''',1)
source=source.replace('        txt.print(iso:"WEATHER COMMANDER CLOSED.\\r\\n")','''        txt.print(iso:"WEATHER COMMANDER CLOSED.\\r\\n")
        sys.wait(1)
        @($9fb5)=1
        sys.wait(1)
        txt.print(iso:"MOUSE PROBE COMPLETE\\r\\n")''')
(ROOT/'build/mouse_probe.p8').write_text(source)
with (ROOT/'build/mouse-probe-build.log').open('w') as log:
 subprocess.run([str(TOOLS/'jre/bin/java'),'-jar',str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),'-target','cx16','-varsgolden','-srcdirs','src','-out','build','build/mouse_probe.p8'],cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)
gif=ROOT/'build/mouse-smoke.gif';gif.unlink(missing_ok=True)
log=ROOT/'build/mouse-smoke.log'
matches=[dict(MATCH,id=408508,name='MADISON AL',label='MADISON, ALABAMA',latitude=34.6993,longitude=-86.7483),MATCH]
with tempfile.TemporaryDirectory(prefix='weather-pointer-') as temp, patch('backend.server.search',return_value=matches), patch('backend.server.fetch_weather',side_effect=lambda cities:weather_fixture()):
 folder=Path(temp)
 for p in (ROOT/'dist/sdcard').iterdir():
  if p.suffix in ('.BIN','.PRG') and p.name not in ('WCDATA.BIN','WCRLIVE.BIN','WCSETUP.BIN','WCQUERY.BIN','WCCITIES.BIN'):(folder/p.name).write_bytes(p.read_bytes())
 (folder/'WCRTEST.BIN').write_bytes(radar_fixture())
 (folder/'WCRTPH.BIN').write_bytes(radar_fixture(1))
 (folder/'WCDATA.BIN').write_bytes(snapshot(weather_fixture(),datetime.now()))
 bridge=Bridge(folder);city_thread=threading.Thread(target=bridge.city_loop,daemon=True);city_thread.start()
 with log.open('w') as output:
  proc=subprocess.Popen([str(TOOLS/'x16emu/x16emu'),'-rom',str(TOOLS/'x16emu/rom.bin'),'-rtc','-scale','1','-sound','none','-echo','iso','-fsroot',temp,'-startin',temp,'-prg',str(ROOT/'build/mouse_probe.prg'),'-run','-gif',str(gif)+',wait'],env=ENV,stdout=output,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+90
   while time.monotonic()<deadline:
    result=log.read_text()
    assert 'MOUSE ROUTE FAILED' not in result,result
    assert 'CITY ADD FAILED' not in result,result
    assert 'COUNTRY SWITCH FAILED' not in result,result
    assert 'COUNTRY RESTORE FAILED' not in result,result
    assert 'LIVE RADAR TRANSITION FAILED' not in result,result
    assert 'DEMO RADAR LABEL FAILED' not in result,result
    if 'MOUSE PROBE COMPLETE' in result:break
    assert proc.poll() is None,result
    time.sleep(.1)
   else:raise AssertionError(log.read_text())
  finally:
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
   bridge.stop.set();city_thread.join(timeout=2)
 assert Bridge(folder).cities[0]==(MATCH['name'],MATCH['latitude'],MATCH['longitude'])
im=Image.open(gif)
assert im.n_frames==n+1,(im.n_frames,n+1)
for i,(name,x,y,page) in enumerate(steps):
 im.seek(i);im.convert('RGB').save(ROOT/'build'/f'pointer-{name}.png')
# Confirm the real renderer follows the exact ROM click tip and switches shapes.
pixels=(ROOT/'dist/sdcard/WCPOINTER.BIN').read_bytes()
palette=(ROOT/'dist/sdcard/WCPAL.BIN').read_bytes()
for name,hot in [('home',False),('national',True),('hourly',True),('wifi',False),('top-left',False)]:
 step=next(s for s in steps if s[0]==name);x,y=step[1:3]
 pic=Image.open(ROOT/'build'/f'pointer-{name}.png').convert('RGB')
 frame=pixels[512 if hot else 0:1024 if hot else 512]
 for dy in range(32):
  for dx in range(32):
   index=(frame[dy*16+dx//2]>>(4 if dx%2==0 else 0))&15
   if not index or not (0<=x+dx<640 and 0<=y-7+dy<480):continue
   expected=(palette[index*2+1]*17,(palette[index*2]>>4)*17,(palette[index*2]&15)*17)
   actual=pic.getpixel((x+dx,y-7+dy))
   assert max(abs(a-b) for a,b in zip(actual,expected))<=20,(name,dx,dy,actual,expected)
print(f'PASS: {n} mouse routes in real r49, offline/live radar in both countries, country switching/restoration, city search/add/persistence, custom pointer pixels/hotspot, all 28 landscapes, and exit.')
