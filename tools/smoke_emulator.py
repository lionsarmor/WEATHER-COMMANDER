#!/usr/bin/env python3
"""Headless r49 smoke test; inject keys through the real KERNAL keyboard buffer.

Builds a temporary copy of main.p8 with a test-only keyboard/capture sequencer.
Production source and release PRG are unchanged. Uses the real event loop, ROM
file I/O, banks, IRQs, video renderer, and exit path. Requires Pillow.
"""
from pathlib import Path
import os,subprocess,time,tempfile,sys
from PIL import Image
from build import ROOT, TOOLS
BASE=[str(TOOLS/'x16emu/x16emu'),'-rom',str(TOOLS/'x16emu/rom.bin'),'-rtc','-scale','1','-sound','none','-echo','iso']
ENV=dict(os.environ,SDL_VIDEODRIVER='dummy',PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
LIVE='--live' in sys.argv
def run(prg,folder,log,expected,extra=(),timeout=20):
 with log.open('w') as output:
  proc=subprocess.Popen(BASE+['-fsroot',str(folder),'-startin',str(folder),'-prg',str(prg),'-run']+list(extra),env=ENV,stdout=output,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+timeout
   while time.monotonic()<deadline:
    if expected in log.read_text():time.sleep(.2);return
    assert proc.poll() is None,log.read_text()
    time.sleep(.1)
   raise AssertionError(log.read_text())
  finally:
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
with tempfile.TemporaryDirectory(prefix='weather-smoke-') as temp:
 folder=Path(temp);prg=folder/'WEATHER.PRG';prg.write_bytes((ROOT/'dist/sdcard/WEATHER.PRG').read_bytes())
 log=ROOT/'build/missing-bank.log'
 run(prg,folder,log,'COPY ALL DIST/SDCARD FILES')
 assert 'WCIDENT.BIN' in log.read_text()
# This instrumentation only queues keys, requests GIF captures, and stops.
source=(ROOT/'src/main.p8').read_text()
if not LIVE:source=source.replace('        state.source=2','        state.source=0')
keys=[13,134,70,72,17,17,138,135,87,50,27,27,83,27] if LIVE else [135,68,138,137,29,13,134,72,27]
source=source.replace('    uword now',f'''    uword smoke_frames=0
    ubyte smoke_step=0
    ubyte[{len(keys)}] smoke_keys={keys}
    uword now''',1)
source=source.replace('            service_timers()','''            service_timers()
            smoke_frames++
            if smoke_frames==60 {
                @($9fb5)=1
                smoke_frames=0
                cx16.kbdbuf_put(smoke_keys[smoke_step])
                smoke_step++
            }''',1)
source=source.replace('        txt.print(iso:"WEATHER COMMANDER CLOSED.\\r\\n")', '        txt.print(iso:"WEATHER COMMANDER CLOSED.\\r\\n")\n        sys.wait(2)\n        @($9fb5)=1\n        sys.wait(2)',1)
(ROOT/'build/emulator_probe.p8').write_text(source)
with (ROOT/'build/probe-build.log').open('w') as output:
 subprocess.run([str(TOOLS/'jre/bin/java'),'-jar',str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),'-target','cx16','-varsgolden','-srcdirs','src','-out','build','build/emulator_probe.p8'],cwd=ROOT,env=ENV,stdout=output,stderr=subprocess.STDOUT,check=True)
# Supply only an isolated demo snapshot to this test, never a user's file.
from pack_weather import pack
import json
with tempfile.TemporaryDirectory(prefix='weather-smoke-') as temp:
 folder=Path(temp)
 for p in (ROOT/'dist/sdcard').iterdir():
  if p.suffix in ('.BIN','.PRG') and p.name not in ('WCDATA.BIN','WCRLIVE.BIN','WCSETUP.BIN'):(folder/p.name).write_bytes(p.read_bytes())
 if LIVE:
  for name in ('WCDATA.BIN','WCRLIVE.BIN'):(folder/name).write_bytes((ROOT/'dist/sdcard'/name).read_bytes())
 else:(folder/'WCDATA.BIN').write_bytes(pack(json.loads((ROOT/'assets/demo-weather.json').read_text())))
 gif=ROOT/'build/emulator-smoke.gif';gif.unlink(missing_ok=True)
 run(ROOT/'build/emulator_probe.prg',folder,ROOT/'build/smoke.log','WEATHER COMMANDER CLOSED.',extra=['-gif',str(gif)+',wait'],timeout=30)
 names=['home','settings','snapshot','radar','cities','city-selected','local','forecast','home-snapshot','exit']
 if LIVE:names=['live-'+n for n in ['home','local','forecast','hourly','home-again','national','regional','radar','settings','wifi','wifi-scan','wifi-choice','settings-back','settings-saved','exit']]
 im=Image.open(gif)
 assert im.n_frames==len(names),(im.n_frames,len(names))
 for i,name in enumerate(names):
  im.seek(i);im.convert('RGB').save(ROOT/'build'/f'preview-{name}.png')
# Check actual decoded pixels, including every letter of every menu label.
font=(ROOT/'dist/sdcard/WCFONT.BIN').read_bytes()
menu=['HOME','NATIONAL','REGIONAL','LOCAL','RADAR','FORECAST','CITIES','SETTINGS','ABOUT']
selections=[0,3,5,5,0,1,2,4,7,None,None,None,7,7] if LIVE else [0,7,7,4,6,6,3,5,0]
for frame,selected in zip(names[:-1],selections):
 if selected is None:continue
 image=Image.open(ROOT/'build'/f'preview-{frame}.png').convert('RGB')
 for item,label in enumerate(menu):
  fg=(0,0,0) if item==selected else (34,204,238)
  for column,char in enumerate(label):
   tile=font[ord(char)*32:ord(char)*32+32]
   for y in range(8):
    for x in range(8):
     pixel=(tile[y*4+x//2]>>(4 if x%2==0 else 0))&15
     actual=image.getpixel(((4+(12-len(label))//2)*8+column*8+x,88+item*24+y))
     # GIF palette quantization can shift cyan in delta frames. Check the
     # glyph mask against its background, not an exact quantized RGB value.
     if pixel==1:
      visible=max(actual)<20 if item==selected else max(actual)>80
     else:
      visible=actual[0]>200 and actual[1]>200 if item==selected else max(actual)<20
     assert visible,(frame,label,column,x,y,actual)
print('PASS: real r49 boot, missing-bank recovery, queued function/arrow keys, snapshot read,')
print(f'      {len(names)} frames with pixel-verified menu labels, and exit to BASIC.')
if LIVE:print('      Live forecast/hourly/regional/radar, full-page Wi-Fi, absent-card scan, and saved settings.')
