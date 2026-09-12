#!/usr/bin/env python3
"""Compile each bounded bank and assemble an SD/HostFS-ready application."""
from pathlib import Path
import os, subprocess, sys, json, re, hashlib, importlib.util, shlex
ROOT=Path(__file__).resolve().parents[1]
DESK=Path.home()/'Desktop/Roddy Software/DESK COMMANDER'
TOOLS=Path(os.environ.get('X16_TOOLS',str(ROOT/'.tools' if (ROOT/'.tools/READY').exists() else DESK/'.tools')))
BUILD=ROOT/'build';OUT=ROOT/'dist/sdcard'
MODULES={'station':'WCIDENT','map':'WCGEOG','conditions':'WCCOND','cities':'WCCITY',
         'forecast':'WCFCST','radar':'WCRADAR','settings':'WCSET','about':'WCABOUT','provider':'WCPROV',
         'network':'WCNET','wifi':'WCWIFI','radar_feed':'WCRFEED','preferences':'WCPREF','city_input':'WCADD','home':'WCHOME','banner':'WCBANNER'}
BANKS={'station':4,'map':5,'conditions':6,'cities':7,'forecast':8,'radar':9,
       'settings':10,'about':11,'provider':13,'network':12,'wifi':14,'radar_feed':15,'preferences':16,'city_input':17,'home':18,'banner':19}
def main():
 if importlib.util.find_spec('PIL') is None:
  command=shlex.join([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements.txt')])
  raise SystemExit(f'Pillow is missing from the Python environment running this build.\nInstall build dependencies with:\n  {command}')
 BUILD.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 java=TOOLS/'jre/bin/java';jar=TOOLS/'prog8/prog8c-12.3.2-all.jar'
 for p in (java,jar,TOOLS/'bin/64tass'):
  if not p.exists():raise SystemExit(f'Missing tool: {p}. Set X16_TOOLS to a toolchain directory (see README).')
 env=dict(os.environ,PATH=str(TOOLS/'bin')+os.pathsep+os.environ['PATH'])
 subprocess.run([sys.executable,'tools/build_assets.py'],cwd=ROOT,check=True)
 sizes={}
 for module,target in [('main','WEATHER')]+[(n+'_overlay',v) for n,v in MODULES.items()]:
  args=[str(java),'-jar',str(jar),'-target','cx16','-srcdirs','src','-out','build','-asmlist']
  if module=='main':args+=['-varsgolden']
  deps=set()
  def visit(name):
   path=ROOT/'src'/(name+'.p8')
   if not path.exists() or path in deps:return
   deps.add(path)
   for imp in re.findall(r'^%import (\w+)',path.read_text(),re.M):visit(imp)
  visit(module)
  digest=hashlib.sha256((' '.join(args)+str(jar.stat().st_mtime_ns)).encode()+b''.join(p.read_bytes() for p in sorted(deps))).hexdigest()
  stamp=BUILD/(module+'.sha256')
  binary=BUILD/(module+('.prg' if module=='main' else '.bin'))
  if not stamp.exists() or stamp.read_text()!=digest or not binary.exists():
   subprocess.run(args+['src/'+module+'.p8'],cwd=ROOT,env=env,check=True)
   stamp.write_text(digest)
  ext='.prg' if module=='main' else '.bin'
  data=(BUILD/(module+ext)).read_bytes()
  limit=0x6000-0x801+2 if module=='main' else 8192
  if len(data)>limit:raise SystemExit(f'{module}: {len(data)} exceeds {limit} bytes')
  (OUT/(target+ext.upper())).write_bytes(data);sizes[target]=len(data)
 (BUILD/'banks.json').write_text(json.dumps(sizes,indent=2)+'\n')
 for obsolete in ('WCNAV.BIN','WCTICK.BIN'):(OUT/obsolete).unlink(missing_ok=True)
 print('\nReady: dist/sdcard/WEATHER.PRG and all bank/graphics files')
 print('Bank sizes:',sizes)
if __name__=='__main__':main()
