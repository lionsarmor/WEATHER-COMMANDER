#!/usr/bin/env python3
"""Run PNG-to-WCR4 in real r49, then compare every pixel and map coordinate."""
from collections import Counter
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from PIL import Image
from build import ROOT, TOOLS
from build_native_assets import build
from test_direct_render import unpack
from backend.maps import philippines
from backend.radar import LEVELS, intensity

SOURCE = r'''
%zeropage basicsafe
%import diskio
%import textio
%import direct_render_mailbox
%import direct_radar_mailbox
%import direct_png_mailbox
%import direct_inflate_mailbox
main {
    extsub @bank 3 $a000 = png_init()
    extsub @bank 24 $a000 = inflate_init()
    extsub @bank 23 $a000 = render_init()
    extsub @bank 23 $a003 = render_begin()
    extsub @bank 23 $a006 = render_next()
    extsub @bank 23 $a009 = render_pack()
    sub start() {
        cx16.rambank(3)
        if diskio.loadlib(iso:"PNG.BIN",$a000)==0 return
        cx16.rambank(24)
        if diskio.loadlib(iso:"INFLATE.BIN",$a000)==0 return
        cx16.rambank(23)
        if diskio.loadlib(iso:"RENDER.BIN",$a000)==0 return
        cx16.rambank(0)
        png_init()
        inflate_init()
        render_init()
        direct_radar_mailbox.country=COUNTRY
        direct_radar_mailbox.downloaded=true
        direct_radar_mailbox.age=300
        render_begin()
        while direct_render_mailbox.phase==1 {
            render_next()
            if direct_png_mailbox.row & 63==0 {
                txt.print(iso:"ROW ")
                txt.print_uw(direct_png_mailbox.row)
                txt.nl()
            }
        }
        render_pack()
        if direct_render_mailbox.phase==3 {
            if diskio.f_open_w(iso:"@:RADAR.BIN") {
                void diskio.f_write($7000,8992)
                diskio.f_close_w()
            }
        }
        txt.print(iso:"RADAR RESULT ")
        txt.print_ub(direct_render_mailbox.phase)
        txt.chrout(32)
        txt.print_ub(direct_inflate_mailbox.error)
        txt.chrout(32)
        txt.print_ub(direct_render_mailbox.step)
        txt.chrout(32)
        txt.print_uw(direct_radar_mailbox.age)
        txt.nl()
        txt.print(iso:"RADAR DONE\r\n")
    }
}
'''

def reference(source,country,step):
    image = Image.open(source).convert('RGBA')
    picture = philippines() if country else Image.new('P',(336,224))
    west,south,east,north = 115.41549141305251,3.801613036809332,129.51730887177652,22.45850950564088
    merc = lambda lat: math.log(math.tan(math.pi/4+math.radians(lat)/2))
    for y in range(56):
        for x in range(84):
            if country:
                lon = 121.2+(x*4+2-142)/15
                lat = 19.5-(y*4+2-12)/15.4
                if not west <= lon < east:
                    continue
                sx = int((lon-west)/(east-west)*image.width)
                sy = int((merc(north)-merc(lat))/(merc(north)-merc(south))*image.height)
                r,g,b,a = image.getpixel((sx,sy))
                rain = (r/255)**2*80
                level = 1+sum(rain>=t for t in (5,6.9,15,30,50,80)) if a>=90 and rain>=.5 else 0
            else:
                level = intensity(image.getpixel((x,y)))
            if level:
                picture.paste(LEVELS[level-1],(x*4,y*4,x*4+4,y*4+4))
    if step>1:
        for y in range(0,224,step):
            for x in range(0,336,step):
                counts = Counter(picture.crop((x,y,x+step,y+step)).getdata())
                color = min(counts,key=lambda c:(-counts[c],c))
                rain = [c for c in LEVELS if c in counts]
                if rain:
                    color = rain[-1]
                picture.paste(color,(x,y,x+step,y+step))
    return picture.tobytes()

def main():
    if len(sys.argv)!=3 or sys.argv[1] not in ('us','ph'):
        raise SystemExit('Usage: tools/smoke_direct_radar.py us|ph radar.png')
    country = int(sys.argv[1]=='ph')
    source = Path(sys.argv[2]).resolve()
    base = build()
    probe = ROOT/'build/native_radar_probe.p8'
    probe.write_text(SOURCE.replace('COUNTRY',str(country)))
    env = dict(os.environ,SDL_VIDEODRIVER='dummy',PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
    with (ROOT/'build/native-radar-probe-build.log').open('w') as log:
        subprocess.run([str(TOOLS/'jre/bin/java'),'-jar',str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),
                        '-target','cx16','-srcdirs','src','-out','build',str(probe)],
                       cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    with tempfile.TemporaryDirectory(prefix='weather-native-radar-') as temp:
        folder = Path(temp)
        (folder/'WCRPNG.BIN').write_bytes(source.read_bytes())
        (folder/'WCPBASE.BIN').write_bytes(base)
        for name in ('png','inflate','render'):
            (folder/(name.upper()+'.BIN')).write_bytes((ROOT/'build'/('direct_'+name+'_overlay.bin')).read_bytes())
        logpath = ROOT/'build'/('native-radar-'+sys.argv[1]+'-rom.log')
        started = time.monotonic()
        with logpath.open('w') as log:
            process = subprocess.Popen([str(TOOLS/'x16emu/x16emu'),'-rom',str(TOOLS/'x16emu/rom.bin'),'-warp',
                                        '-rtc','-sound','none','-echo','iso','-fsroot',str(folder),'-startin',str(folder),
                                        '-prg',str(ROOT/'build/native_radar_probe.prg'),'-run'],
                                       env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                while 'RADAR DONE' not in logpath.read_text():
                    assert process.poll() is None,logpath.read_text()
                    assert time.monotonic()-started<240,logpath.read_text()
                    time.sleep(.2)
            finally:
                process.terminate()
                process.wait(timeout=5)
        result = re.search(r'RADAR RESULT (\d+) (\d+) (\d+) (\d+)',logpath.read_text())
        assert result and result.groups()[:2]==('3','0'),logpath.read_text()
        raw = (folder/'RADAR.BIN').read_bytes()
        assert unpack(raw)==reference(source,country,int(result[3])), 'Native radar differs from geographic reference'
        (ROOT/'build'/('native-'+sys.argv[1]+'-radar.bin')).write_bytes(raw)
        print(f'PASS: {sys.argv[1].upper()} PNG-to-map matches every reference pixel; {raw[4]} tiles, {result[3]}px simplification, {int(result[4])-300}s emulated processing ({time.monotonic()-started:.1f}s warp wall time).')

if __name__=='__main__':
    main()
