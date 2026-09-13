#!/usr/bin/env python3
"""Native PNG/radar inside the real application event loop and r49 ROM.

Only the downloaded-image handoff is a fixture. All PNG, banked history,
cooperative scheduling, map caching, UI routing and VRAM uploads are native.
Public request orchestration and actual UART framing have separate tests.
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image
from build import ROOT, TOOLS
from package import RUNTIME_FILES
from smoke_direct_radar import reference
from test_direct_render import unpack

country=int(sys.argv[1]=='ph')
image_path=Path(sys.argv[2]).resolve()
env=dict(os.environ,SDL_VIDEODRIVER='dummy',PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
network='''%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import network
main {
    %jmptable (network.action, network.weather, main.downloaded, network.city)
    sub start() { }
    sub downloaded() {
        direct_radar_mailbox.country=state.country
        direct_radar_mailbox.age=300
        direct_radar_mailbox.downloaded=true
    }
}
'''
source=(ROOT/'src/main.p8').read_text()
source=source.replace('%import direct_locations','%import direct_locations\n%import direct_png_mailbox\n%import direct_radar_mailbox')
source=source.replace('    uword now','    uword probe_row=65535\n    uword probe_i\n    ubyte probe_routes=0\n    uword now',1)
source=source.replace('''        preferences_load()
        provider_refresh()
        radar_feed_refresh()''',f'''        preferences_load()
        state.source=0
        state.country={country}
        state.country_choice={country}
        provider_refresh()
        state.source=2
        state.automatic=false
        state.page=state.RADAR
        radar_feed_refresh()''')
source=source.replace('''            radar_feed_step()
''','''            if direct_render_mailbox.phase==1 and direct_png_mailbox.row & 127==0 and probe_row!=direct_png_mailbox.row {
                probe_row=direct_png_mailbox.row
                probe_routes++
                if probe_routes & 1==0 key=134
                else key=138
                handle_key()
                @($9fb5)=1
                ; Simulate the documented HTTP scratch overwrite between rows.
                for probe_i in 0 to 8191 @($7000+probe_i)=165
            }
            radar_feed_step()
''')
source=source.replace('''            service_timers()
''','''            service_timers()
            if direct_render_mailbox.phase==3 or direct_render_mailbox.phase==4 {
                key=138
                handle_key()
                @($9fb5)=1
                sys.wait(1)
                if state.radar_ready and diskio.f_open_w(iso:"@:RESULT.BIN") {
                    void diskio.f_write($7000,8992)
                    diskio.f_close_w()
                }
                txt.print(iso:"NATIVE APP RESULT ")
                txt.print_ub(direct_render_mailbox.phase)
                txt.chrout(32)
                txt.print_ub(probe_routes)
                txt.chrout(32)
                txt.print_uw(direct_radar_mailbox.age)
                txt.nl()
                running=false
            }
''')
for name,text in (('native_network_probe',network),('native_app_probe',source)):
 path=ROOT/'build'/(name+'.p8');path.write_text(text)
 with (ROOT/'build'/(name+'-build.log')).open('w') as log:
  subprocess.run([str(TOOLS/'jre/bin/java'),'-jar',str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),'-target','cx16',*(['-varsgolden'] if name=='native_app_probe' else []),'-srcdirs','src','-out','build',str(path)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with tempfile.TemporaryDirectory(prefix='weather-native-app-') as temp:
 folder=Path(temp)
 for name in RUNTIME_FILES:
  (folder/name).write_bytes((ROOT/'dist/sdcard'/name).read_bytes())
 for name in ('WCPBASE.BIN','WCDMUS.BIN','WCDMPH.BIN'):
  (folder/name).write_bytes((ROOT/'dist/sdcard'/name).read_bytes())
 (folder/'WCNET.BIN').write_bytes((ROOT/'build/native_network_probe.bin').read_bytes())
 (folder/'WCRPNG.BIN').write_bytes(image_path.read_bytes())
 logpath=ROOT/'build'/('native-app-'+sys.argv[1]+'.log')
 gif=ROOT/'build'/('native-app-'+sys.argv[1]+'.gif');gif.unlink(missing_ok=True)
 started=time.monotonic()
 with logpath.open('w') as log:
  process=subprocess.Popen([str(TOOLS/'x16emu/x16emu'),'-rom',str(TOOLS/'x16emu/rom.bin'),'-warp','-rtc','-sound','none','-echo','iso','-fsroot',str(folder),'-startin',str(folder),'-prg',str(ROOT/'build/native_app_probe.prg'),'-run','-gif',str(gif)+',wait'],env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   while 'WEATHER COMMANDER CLOSED.' not in logpath.read_text():
    assert process.poll() is None,logpath.read_text()
    assert time.monotonic()-started<180,logpath.read_text()
    time.sleep(.2)
  finally:
   process.terminate();process.wait(timeout=5)
 result=re.search(r'NATIVE APP RESULT (\d+) (\d+) (\d+)',logpath.read_text())
 assert result and result[1]=='3',logpath.read_text()
 raw=(folder/'RESULT.BIN').read_bytes()
 # Actual native renderer may simplify to stay inside its bounded tile budget.
 assert any(unpack(raw)==reference(image_path,country,step) for step in (1,2,4,8))
 assert int(result[2])==(9 if country else 1)
 frames=Image.open(gif);frames.seek(frames.n_frames-1);frames.convert('RGB').save(ROOT/'build'/('native-app-'+sys.argv[1]+'.png'))
 print(f'PASS: {sys.argv[1].upper()} radar in full r49 app, {result[2]} UI transitions and HTTP scratch overwrites, geographic pixels exact; {int(result[3])-300}s emulated processing.')
