#!/usr/bin/env python3
"""Check unpublished native components without changing any release files."""
import os
import subprocess
import sys
from build import ROOT, TOOLS

MODULES = {'direct_http':20, 'direct_weather_decode':21, 'direct_weather':22,
           'direct_inflate':24, 'direct_png':3, 'direct_crypto':2}
TESTS = ('http', 'download', 'json', 'weather', 'inflate', 'png', 'crypto', 'time')

def main():
    (ROOT/'build').mkdir(exist_ok=True)
    env = dict(os.environ, PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
    for module, bank in MODULES.items():
        logpath = ROOT/'build'/(module+'-compile.log')
        with logpath.open('w') as log:
            result = subprocess.run([str(TOOLS/'jre/bin/java'), '-jar', str(TOOLS/'prog8/prog8c-12.3.2-all.jar'),
                                     '-target', 'cx16', '-srcdirs', 'src', '-out', 'build', '-asmlist',
                                     'src/'+module+'_overlay.p8'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(logpath.read_text())
        size = (ROOT/'build'/(module+'_overlay.bin')).stat().st_size
        assert size <= 8192, (module, size)
        print(f'Bank {bank:2}: {module:24} {size:4} bytes', flush=True)
    for name in TESTS:
        subprocess.run([sys.executable, 'tools/test_direct_'+name+'.py'], cwd=ROOT, check=True)
    print('PASS: native component checks. Production app integration is still pending.')

if __name__ == '__main__':
    main()
