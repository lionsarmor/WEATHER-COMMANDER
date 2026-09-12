#!/usr/bin/env python3
"""Compare native PNG scanlines with Pillow using r49 ROM disk and bank calls.

Pass a downloaded public radar PNG as the argument. The source is copied to
an isolated temporary SD folder; application/user files are never touched.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image
from build import ROOT, TOOLS

SOURCE = r'''
%zeropage basicsafe
%import diskio
%import textio
%import direct_png_mailbox
%import direct_inflate_mailbox
main {
    extsub @bank 3 $a000 = png_init()
    extsub @bank 3 $a003 = png_open()
    extsub @bank 3 $a006 = png_row()
    extsub @bank 3 $a00c = png_close()
    extsub @bank 24 $a000 = inflate_init()
    sub start() {
        cx16.rambank(3)
        if diskio.loadlib(iso:"PNG.BIN",$a000)==0 return
        cx16.rambank(24)
        if diskio.loadlib(iso:"INFLATE.BIN",$a000)==0 return
        cx16.rambank(0)
        png_init()
        inflate_init()
        png_open()
        txt.print(iso:"PNG OPEN ")
        txt.print_uw(direct_png_mailbox.width)
        txt.chrout(120)
        txt.print_uw(direct_png_mailbox.height)
        txt.nl()
        if not diskio.f_open_w(iso:"@:WCRRAW.BIN") return
        while direct_inflate_mailbox.error==0 and not direct_png_mailbox.complete {
            png_row()
            if direct_png_mailbox.ready {
                if not diskio.f_write($7001,direct_png_mailbox.row_bytes) {
                    direct_inflate_mailbox.error=8
                    break
                }
                if direct_png_mailbox.row & 63==0 {
                    txt.print(iso:"ROW ")
                    txt.print_uw(direct_png_mailbox.row)
                    txt.nl()
                }
            }
        }
        png_close()
        diskio.f_close_w()
        txt.print(iso:"PNG RESULT ")
        txt.print_ub(direct_inflate_mailbox.error)
        txt.chrout(32)
        txt.print_ub(direct_png_mailbox.complete as ubyte)
        txt.nl()
        txt.print(iso:"PNG DONE\r\n")
    }
}
'''

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: tools/smoke_direct_png.py radar.png')
    source = Path(sys.argv[1]).resolve()
    expected = Image.open(source).tobytes()
    probe = ROOT / 'build/native_png_probe.p8'
    probe.write_text(SOURCE)
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
    with (ROOT/'build/native-png-probe-build.log').open('w') as log:
        subprocess.run([str(TOOLS/'jre/bin/java'), '-jar', str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),
                        '-target', 'cx16', '-srcdirs', 'src', '-out', 'build', str(probe)],
                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    with tempfile.TemporaryDirectory(prefix='weather-native-png-') as temp:
        folder = Path(temp)
        (folder/'WCRPNG.BIN').write_bytes(source.read_bytes())
        for name, target in (('direct_png', 'PNG'), ('direct_inflate', 'INFLATE')):
            (folder/(target+'.BIN')).write_bytes((ROOT/'build'/(name+'_overlay.bin')).read_bytes())
        logpath = ROOT/'build/native-png-rom.log'
        with logpath.open('w') as log:
            command = [str(TOOLS/'x16emu/x16emu'), '-rom', str(TOOLS/'x16emu/rom.bin'), '-warp',
                       '-sound', 'none', '-echo', 'iso', '-fsroot', str(folder), '-startin', str(folder),
                       '-prg', str(ROOT/'build/native_png_probe.prg'), '-run']
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
            started = time.monotonic()
            try:
                while 'PNG DONE' not in logpath.read_text():
                    if time.monotonic()-started > 240:
                        raise AssertionError('Native decoder timed out: '+logpath.read_text())
                    assert process.poll() is None, logpath.read_text()
                    time.sleep(.2)
            finally:
                process.terminate()
                process.wait(timeout=5)
        result = logpath.read_text()
        assert 'PNG RESULT 0 1' in result, result
        decoded = (folder/'WCRRAW.BIN').read_bytes()
        assert decoded == expected, f'Native image mismatch: {len(decoded)} vs {len(expected)} bytes'
        print(f'PASS: r49 decoded {len(decoded):,} image bytes exactly, with real ROM bank and file calls ({time.monotonic()-started:.1f}s).')

if __name__ == '__main__':
    main()
