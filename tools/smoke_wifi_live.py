#!/usr/bin/env python3
"""Real app, ROM, emulated UART/TLS and public APIs; no weather/network fixtures."""
import os
from pathlib import Path
import subprocess
import time

from build import ROOT, TOOLS
from package import RUNTIME_FILES

emulator = Path(os.environ.get('WEATHER_WIFI_EMULATOR', str(Path.home()/'Desktop/X16-emulator-wifi-support/x16-emulator/build/x16emu')))
folder = ROOT/'build/wifi-live-sd'
folder.mkdir(exist_ok=True)
for name in RUNTIME_FILES:
    (folder/name).write_bytes((ROOT/'dist/sdcard'/name).read_bytes())
for name in ('WCSETUP.BIN', 'PROGRESS.BIN', 'RESULT.BIN', 'WCRPNG.BIN'):
    (folder/name).unlink(missing_ok=True)
source = (ROOT/'src/main.p8').read_text()
source = source.replace('    uword now', '''    uword wifi_ticks=0
    ubyte wifi_test_step=0
    ubyte[6] wifi_keys=[135,87,50,13,13,13]
    sub wifi_progress() {
        @($9400)=wifi_test_step
        if diskio.f_open_w(iso:"@:PROGRESS.BIN") {
            void diskio.f_write($9400,1)
            void diskio.f_write($9800,128)
            void diskio.f_write($69c0,64)
            void diskio.f_write($6d70,16)
            void diskio.f_write($6f22,16)
            diskio.f_close_w()
        }
    }
    uword now''', 1)
source = source.replace('            service_timers()', '''            service_timers()
            wifi_ticks++
            if wifi_ticks==30 and wifi_test_step<6 {
                key=wifi_keys[wifi_test_step]
                handle_key()
                wifi_test_step++
                wifi_ticks=0
                wifi_progress()
            }
            if wifi_test_step==6 {
                wifi_progress()
                if state.wifi_step!=4 or direct_render_mailbox.phase!=1 {
                    if state.wifi_step==4 {
                        network_mailbox.action=4
                        finish_wifi_action()
                        wifi_progress()
                    }
                    if state.wifi_step==4 and diskio.f_open_w(iso:"@:RESULT.BIN") {
                        void diskio.f_write($6000,1024)
                        diskio.f_close_w()
                    }
                    txt.print(iso:"WIFI LIVE RESULT ")
                    txt.print_ub(state.wifi_step)
                    txt.chrout(32)
                    txt.print_ub(state.status)
                    txt.chrout(32)
                    txt.print_ub(state.radar_ready as ubyte)
                    txt.nl()
                    running=false
                }
            }
''', 1)
probe = ROOT/'build/wifi_live_probe.p8'
probe.write_text(source)
env = dict(os.environ, SDL_VIDEODRIVER='dummy', PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
with (ROOT/'build/wifi-live-compile.log').open('w') as log:
    subprocess.run([str(TOOLS/'jre/bin/java'), '-jar', str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),
                    '-target', 'cx16', '-varsgolden', '-srcdirs', 'src', '-out', 'build', str(probe)],
                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
logpath = ROOT/'build/wifi-live.log'
with logpath.open('w') as log:
    process = subprocess.Popen([str(emulator), '-rom', str(emulator.parent/'rom.bin'), '-wifi',
                                '-rtc', '-sound', 'none', '-echo', 'iso', '-fsroot', str(folder),
                                '-startin', str(folder), '-prg', str(probe.with_suffix('.prg')), '-run'],
                               env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic()+240
        while 'WEATHER COMMANDER CLOSED.' not in logpath.read_text():
            assert process.poll() is None, logpath.read_text()
            assert time.monotonic()<deadline, 'Timed out; inspect build/wifi-live-sd/PROGRESS.BIN and wifi-live.log'
            time.sleep(.25)
    finally:
        process.terminate()
        process.wait(timeout=5)
progress = (folder/'PROGRESS.BIN').read_bytes()
assert 'WIFI LIVE RESULT 4 3' in logpath.read_text(), (logpath.read_text(), progress.hex())
assert progress[134]==3, 'Wi-Fi association was lost after downloading weather/radar'
weather = (folder/'RESULT.BIN').read_bytes()
assert len(weather)==1024 and weather[:6]==b'WCW2\x02\x0a' and weather[6]==1
print('PASS: actual Wi-Fi scan, open-network join, TLS and ten-city live weather through the full emulator.')
print(logpath.read_text().split('WIFI LIVE RESULT ')[-1].splitlines()[0]+' (wizard step, weather status, radar ready)')
