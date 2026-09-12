#!/usr/bin/env python3
"""Execute the built 65C02 core/banks, with banked RAM, VERA, and ROM stubs.

Checks real compiled instructions, not a rewrite of the Prog8 logic. The real
r49 emulator is still required to validate the display, ROM I/O, and mouse.
"""
from pathlib import Path
import json,re,sys,copy,struct
from collections import deque
from datetime import datetime
try:
 from py65.devices.mpu65c02 import MPU
except ImportError:
 raise SystemExit('Run .venv/bin/python tools/check.py (install py65 into .venv first).')
from pack_weather import pack
ROOT=Path(__file__).resolve().parents[1]
from build import MODULES, BANKS

def labels(name):
 result={}
 for line in (ROOT/'build'/f'{name}.vice-mon-list').read_text().splitlines():
  bits=line.split()
  if len(bits)>=3 and bits[0]=='al':result[bits[2].lstrip('.')]=int(bits[1],16)
 scopes=[]
 for line in (ROOT/'build'/f'{name}.asm').read_text().splitlines():
  scope=re.match(r'^(\w+)\s+\.proc',line)
  variable=re.match(r'^(p8v_\w+)\s*=\s*(\d+)\s*; zp',line)
  if scope:scopes.append(scope[1])
  elif line.strip()=='.pend' and scopes:scopes.pop()
  elif variable:result[':'.join(scopes+[variable[1]])]=int(variable[2])
 return result

class Memory(list):
 def __init__(self):
  super().__init__([0]*65536);self.banks=[bytearray(8192) for _ in range(64)]
  self.vram=bytearray(131072);self.writes=[]
  self.uart=False;self.rx=deque();self.tx=bytearray();self.commands=[];self.wire=b''
 def __getitem__(self,a):
  if isinstance(a,slice):return [self[i] for i in range(*a.indices(65536))]
  if 0xa000<=a<0xc000:return self.banks[super().__getitem__(0)][a-0xa000]
  if a==0x9fe7 and not self.uart:return 0
  if self.uart and a==0x9fe5:return 0x20|int(bool(self.rx))
  if self.uart and a==0x9fe0 and not super().__getitem__(0x9fe3)&0x80:return self.rx.popleft() if self.rx else 0
  return super().__getitem__(a)
 def __setitem__(self,a,v):
  if isinstance(a,slice):
   for i,x in zip(range(*a.indices(65536)),v):self[i]=x
  elif 0xa000<=a<0xc000:self.banks[super().__getitem__(0)][a-0xa000]=v
  elif self.uart and a==0x9fe0 and not self[0x9fe3]&0x80:
   if v==13:
    command=bytes(self.tx);self.commands.append(command);self.tx.clear()
    reply=b'\r\nOK\r\n'
    if command==b'ATW10':reply=b'Home Network (-42)*\r\nSecond WiFi (-65)*\r\nOK\r\n'
    if command==b'ATI2':reply=b'192.168.1.50\r\nOK\r\n'
    if command.startswith(b'AT&G'):reply=b'WC2:'+self.wire.hex().upper().encode()+b'\r\nOK\r\n'
    self.rx.extend(reply)
   elif v not in (3,10):self.tx.append(v)
  elif a==0x9f23:
   addr=self[0x9f20]+self[0x9f21]*256+(self[0x9f22]&1)*65536
   self.vram[addr]=v;self.writes.append(addr)
   inc=[0,1,2,4,8,16,32,64,128,256,512,40,80,160,320,640][self[0x9f22]>>4]
   addr=(addr+inc)&0x1ffff
   super().__setitem__(0x9f20,addr&255);super().__setitem__(0x9f21,(addr>>8)&255)
   super().__setitem__(0x9f22,(self[0x9f22]&0xf0)|(addr>>16))
  else:super().__setitem__(a,v)

class Harness:
 def __init__(self):
  self.m=Memory();self.cpu=MPU(memory=self.m);self.symbols={0:labels('main')}
  self.hooks={};self.fars=[];self.ticks=0;self.file=None;self.clock=None;self.hour=14;self.radar=None;self.radar_current=None
  self.radar_samples={name:(ROOT/'dist/sdcard'/name).read_bytes() for name in ('WCRDEMO.BIN','WCRDPH.BIN')}
  binary=(ROOT/'build/main.prg').read_bytes();addr=int.from_bytes(binary[:2],'little');self.m[addr:addr+len(binary)-2]=binary[2:]
  for name,b in BANKS.items():
   self.symbols[b]=labels(name+'_overlay');data=(ROOT/'dist/sdcard'/f'{MODULES[name]}.BIN').read_bytes()
   assert len(data)<=8192;self.m.banks[b][:len(data)]=data
  for b,name in enumerate(['NAT','REG','RAD','BLK'],32):
   data=(ROOT/'dist/sdcard'/f'WC{name}.BIN').read_bytes();self.m.banks[b][:len(data)]=data
  for b,name in [(30,'WCHART'),(31,'WCPH')]:
   data=(ROOT/'dist/sdcard'/f'{name}.BIN').read_bytes();self.m.banks[b][:len(data)]=data
  for i in range(28):
   data=(ROOT/'dist/sdcard'/f'WCSC{i:02}.BIN').read_bytes();assert len(data)==6080
   self.m.banks[36+i][:len(data)]=data
  for name,addr in [('WCPOINTER',0x18000),('WCTILES',0),('WCMAP',0x8000),('WCFONT',0x10000),('WCPAL',0x1fa00)]:
   data=(ROOT/'dist/sdcard'/f'{name}.BIN').read_bytes();self.m.vram[addr:addr+len(data)]=data
  self.hook(0,'cbm:RDTIM16',lambda:self.ay(self.ticks))
  self.hook(13,'diskio:f_open',lambda:self.ay(int(self.file is not None)))
  self.hook(13,'diskio:f_close',lambda:None)
  self.hook(13,'diskio:f_read',self.read_file)
  self.hook(15,'diskio:f_open',self.radar_open)
  self.hook(15,'diskio:f_close',lambda:None)
  self.hook(15,'diskio:f_read',lambda:self.read_file(15))
  for b in BANKS.values():self.run(b,0xa000)
  self.m[0x9803]=60;self.m[0x9808]=1
  self.run(13,0xa003)
  self.set(0,'p8b_main:p8v_background',255)
 def ay(self,value):self.cpu.a=value&255;self.cpu.y=value>>8
 def hook(self,b,name,action):self.hooks[(b,self.symbols[b][name])]=action
 def set(self,b,name,value):
  addr=self.symbols[b][name];old=self.m[0];self.m[0]=b;self.m[addr]=value&255;self.m[0]=old
 def word(self,b,name,value):
  addr=self.symbols[b][name];self.m[addr]=value&255;self.m[addr+1]=value>>8
 def radar_open(self):
  address=self.cpu.a+self.cpu.y*256;name=bytearray()
  while self.m[address]:name.append(self.m[address]);address+=1
  self.radar_current=self.radar if name==b'WCRLIVE.BIN' else self.radar_samples.get(name.decode())
  self.ay(int(self.radar_current is not None))
 def read_file(self,bank=13):
  sym=self.symbols[bank];p=sym['diskio:f_read:bufferpointer'];n=sym['diskio:f_read:num_bytes']
  addr=self.m[p]+self.m[p+1]*256;size=self.m[n]+self.m[n+1]*256
  assert (addr,size)==((0x6400,1025) if bank==13 else (0x7000,8993))
  data=((self.file if bank==13 else self.radar_current) or b'')[:size];self.m[addr:addr+len(data)]=data;self.ay(len(data))
 def run(self,b,routine,budget=2_000_000):
  self.m[0]=b;self.cpu.sp=0xff;self.cpu.stPushWord(0x2ff)
  self.cpu.pc=self.symbols[b][routine] if isinstance(routine,str) else routine
  for _ in range(budget):
   pc=self.cpu.pc
   if pc==0x300:return
   if self.m[pc]==0xcb:self.cpu.pc+=1;continue  # a completed video-frame wait
   if pc==0xff6e:
    ret=self.cpu.stPopWord();addr=self.m[ret+1]+self.m[ret+2]*256;bank=self.m[ret+3]
    self.fars.append((self.m[0],ret+4));self.m[0]=bank
    self.cpu.stPushWord(0xfeff);self.cpu.pc=addr;continue
   if pc==0xff00:
    bank,ret=self.fars.pop();self.m[0]=bank;self.cpu.pc=ret;continue
   if pc==0xff50:
    self.m[2:10]=self.clock or [126,9,10,self.hour,30,15,0,4];self.cpu.pc=self.cpu.stPopWord()+1;continue
   hook=self.hooks.get((self.m[0],pc)) or self.hooks.get((0,pc))
   if hook:
    hook();self.cpu.pc=self.cpu.stPopWord()+1;continue
   assert pc<0xc000,(b,routine,hex(pc),'unexpected ROM call')
   self.cpu.step()
  raise AssertionError((b,routine,'instruction budget exhausted',hex(self.cpu.pc)))
 def text(self,x,y,n):
  addr=(0x1b000 if self.m[0x9809] else 0xc000)+y*256+x*2
  result=[]
  for i in range(n):
   tile=self.m.vram[addr+i*2]+((self.m.vram[addr+i*2+1]&3)<<8)
   result.append(32+(tile-512)//2 if 512<=tile<704 else tile&255)
  return bytes(result)
 def key(self,k):self.set(0,'p8b_main:p8v_key',k);self.run(0,'p8b_main:p8s_handle_key')

def join_failure_check():
 test=Harness()
 test.set(12,'p8b_network_driver:p8v_modem_present',1)
 test.m[0x69c5]=3
 test.m[0x69c0]=3
 test.m[0x6950:0x6955]=list(b'Home\0')
 test.m[0x6980:0x6987]=list(b'secret\0')
 test.hook(12,'p8b_network_driver:p8s_send_command',lambda:test.ay(0))
 test.run(12,0xa003)
 assert test.m[0x69c5]==2,'A failed reconnect retained its old connected flag'
 assert not any(test.m[0x6980:0x69c0]),'Failed join retained its password'
if '--join-only' in sys.argv:
 join_failure_check();print('PASS: failed modem reconnect stays on password step and clears secret.');sys.exit(0)

def centered_bar(h,x,y,w,height):
 # Decode the compiled screen's actual glyph pixels, including both halves.
 font=(ROOT/'dist/sdcard/WCFONT.BIN').read_bytes()
 base=0x1b000 if h.m[0x9809] else 0xc000
 ink=[]
 for py in range(height*8):
  for px in range(w*8):
   addr=base+(y+py//8)*256+(x+px//8)*2
   tile=h.m.vram[addr]+((h.m.vram[addr+1]&3)<<8)
   data=font[tile*32+(py%8)*4+(px%8)//2]
   if ((data>>(4 if px%2==0 else 0))&15)==1:ink.append((px,py))
 assert ink,(x,y,'missing label')
 left=min(p[0] for p in ink);right=w*8-1-max(p[0] for p in ink)
 top=min(p[1] for p in ink);bottom=height*8-1-max(p[1] for p in ink)
 assert (top,bottom)==((height*8-7)//2,(height*8-7+1)//2),(x,y,top,bottom)
 # Center monospaced cells; punctuation can have a narrower ink outline.
 assert abs(left//8-right//8)<=1,(x,y,'horizontal centering',left,right)

h=Harness();demo=bytes(h.m[0x9840:0x9890])
assert demo[0]==54 and demo[7*8]==52
for page in list(range(10))+[11]:
 h.m[0x9800]=page;h.m.writes.clear();h.run(0,'p8b_main:p8s_redraw')
 assert h.m[0]==0,'Bank call did not restore resident bank'
 assert all(0x4e80<=a<0x77c0 or 0x8000<=a<0x10000 or 0x1b000<=a<0x1f000 for a in h.m.writes),'Panel wrote outside tilemaps'
 assert h.text(66,11,9)==b'CURRENTLY'
 assert h.text(2,42,13)==b'SELECT A CITY'
 assert any(h.text(18,9,42))
 for i,label in enumerate(['HOME','NATIONAL','REGIONAL','LOCAL','RADAR','FORECAST','CITIES','SETTINGS','ABOUT']):
  assert h.text(4+(12-len(label))//2,11+i*3,len(label))==label.encode(),(page,label)
 bars={
  0:[(20,14,18,2),(40,14,18,2),(20,30,18,3),(40,30,18,3)],
  2:[(20,12,38,2)],
  3:[(20,12,38,2),(20,26,18,2),(40,26,18,2),(20,39,10,2),(31,39,16,2),(48,39,10,2)],
  4:[(22,20,34,2),(24,31,12,2),(38,31,16,2)],
  5:[(20,15,38,2),(20,37,38,3)],
  6:[(20,12,38,2),(20,26,18,2),(40,26,18,2),(20,36,38,2),(31,39,16,2)],
  7:[(19,13,40,3),(19,16,40,2),(19,38,40,3),(20,35,7,2),(28,35,30,2)]+[(x,y,w,3) for y in (19,23,27,31) for x,w in ((20,3),(24,19),(44,14))],
  8:[(20,12,38,2),(20,24,38,2),(20,39,38,2)],
  9:[(20,12,38,2),(20,26,38,2)],
  11:[(20,20,23,3),(45,20,13,3)]}
 for rect in bars.get(page,[]):centered_bar(h,*rect)

# The prominent clock and location have true 14-pixel lettering, centered in 16-pixel lines.
def banner_pixel(x,y):
 tile=(y//8)*35+x//8
 packed=h.m.vram[0x4e80+tile*32+(y%8)*4+(x%8)//2]
 return (packed>>(4 if x%2==0 else 0))&15
for top,color in [(0,6),(16,5)]:
 points=[(x,y) for y in range(top,top+16) for x in range(280) if banner_pixel(x,y)==color]
 assert points
 assert min(y for x,y in points)==top+1 and max(y for x,y in points)==top+14
 assert abs(min(x for x,y in points)-(279-max(x for x,y in points)))<=4
# Compiled input routing, city wrap, settings and negative Celsius formatting.
for step in range(5):
 h.m[0x9800]=10;h.m[0x981a]=step
 h.run(0,'p8b_main:p8s_redraw')
 for rect in [(4,9,59,3),(64,9,12,3),(8,48,64,3),(8,54,20,3),(42,54,30,3)]:centered_bar(h,*rect)
 if step==0:
  centered_bar(h,8,19,64,2);centered_bar(h,8,32,64,2)
 elif step==1:centered_bar(h,8,17,64,2)
 elif step==2:centered_bar(h,8,18,64,2)
 else:centered_bar(h,8,19,64,2)
h.m[0x981a]=0
h.m[0x9800]=0
# Station transitions use the RTC and touch only the module-owned rectangle.
station_cells={0xab78+row*256+col for row in range(10) for col in range(38)}
scene_cells=set(range(0x6000,0x77c0))
for hour,phase in [(0,3),(4,3),(5,0),(7,0),(8,1),(16,1),(17,2),(19,2),(20,3),(23,3),(0,3)]:
 h.hour=hour;h.m.writes.clear();h.run(0,'p8b_main:p8s_clock_draw')
 assert h.m[0]==0 and h.m[0x980a]==hour
 assert {a for a in h.m.writes if a<0xc000}<=station_cells|scene_cells|set(range(0x4e80,0x6000))|{0x8158+row*256+col for row in range(4) for col in range(70)}
 actual=bytes(h.m.vram[a] for a in sorted(station_cells))
 assert actual==b''.join(struct.pack('<H',(768+i)|((11+phase)<<12)) for i in range(190)),(hour,phase)
 assert h.m.vram[0x6000:0x77c0]==(ROOT/'dist/sdcard'/f'WCSC{phase:02}.BIN').read_bytes()
 h.m.writes.clear();h.run(0,'p8b_main:p8s_clock_draw')
 assert not (station_cells|scene_cells).intersection(h.m.writes),'Unchanged station phase was repainted'
# All themes stream to the same reserved tiles without changing any other art.
for theme in range(7):
 h.m[0x9816]=theme;h.m.writes.clear();h.run(0,'p8b_main:p8s_scene_update')
 assert h.m[0]==0 and set(h.m.writes)<=scene_cells
 assert h.m.vram[0x6000:0x77c0]==(ROOT/'dist/sdcard'/f'WCSC{theme*4+3:02}.BIN').read_bytes()
h.m[0x9816]=0
h.hour=14
for key,page in [(133,9),(137,6),(134,5),(138,4),(135,7),(72,0)]:
 h.key(key);assert h.m[0x9800]==page,(key,h.m[0x9800])
h.key(78);assert h.m[0x9800]==11
h.key(27);assert h.m[0x9800]==6
h.m[0x9801]=0;h.key(157);assert h.m[0x9801]==9
h.key(29);assert h.m[0x9801]==0
h.key(135);h.key(85);assert h.m[0x9802]==1
h.m[0x9840]=14;h.run(0,'p8b_main:p8s_redraw')
assert h.text(17,44,4)==b'-10\x7f',h.text(17,44,4)
h.key(85);h.m[0x9840]=(-128)&255;h.run(0,'p8b_main:p8s_redraw')
assert h.text(17,44,5)==b'-128\x7f'
h.key(84);assert h.m[0x9803]==120
h.key(84);assert h.m[0x9803]==30
h.key(84);assert h.m[0x9803]==60
h.key(65);assert h.m[0x9808]==0
h.key(65);assert h.m[0x9808]==1
# The snapshot provider must reject bad reads transactionally.
doc=json.loads((ROOT/'assets/demo-weather.json').read_text());good=pack(doc)
assert len(good)==128
h.m[0x9804]=1
for bad in [None,b'',good[:-1],good+b'x',b'BAD!'+good[4:],good[:4]+b'\x02'+good[5:],good[:8]+b'\0\0'+good[10:]]:
 before=bytes(h.m[0x9840:0x9890]);h.file=bad;h.run(13,0xa003)
 assert h.m[0x9805]==2 and bytes(h.m[0x9840:0x9890])==before
for offset,value in [(17,4),(18,101),(19,201),(22,201),(23,101)]:
 bad=bytearray(good);bad[offset]=value;bad[8:10]=sum(bad[16:96]).to_bytes(2,'little')
 h.file=bad;before=bytes(h.m[0x9840:0x9890]);h.run(13,0xa003)
 assert h.m[0x9805]==2 and bytes(h.m[0x9840:0x9890])==before
h.file=good;h.run(13,0xa003)
assert h.m[0x9805]==1 and bytes(h.m[0x9840:0x9890])==demo
# Repeat reads reset the checksum and accept complete replacement data.
doc['cities'][0]['temperature_f']=-12;h.file=pack(doc);h.run(13,0xa003)
assert h.m[0x9840]==244 and h.m[0x9805]==1
bad_doc=copy.deepcopy(doc);bad_doc['cities'][0]['humidity_pct']=101
try:pack(bad_doc);raise AssertionError('packer accepted invalid humidity')
except ValueError:pass
# Exercise compiled scheduler at the exact minute and across 16-bit rollover.
h.m[0x9804]=0;h.m[0x9803]=60;h.m[0x9808]=1
h.word(0,'p8b_main:p8v_last_refresh',0);cycles=h.m[0x9806]
h.ticks=3599;h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9806]==cycles
h.ticks=3600;h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9806]==(cycles+1)&255
h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9806]==(cycles+1)&255
h.word(0,'p8b_main:p8v_last_refresh',65000);h.ticks=(65000+3600)&65535
h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9806]==(cycles+2)&255
h.m[0x9808]=0;h.ticks+=7200;h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9806]==(cycles+2)&255
sizes=json.loads((ROOT/'build/banks.json').read_text());assert all(n<=8192 for k,n in sizes.items() if k!='WEATHER')
sys.path.insert(0,str(ROOT))
from backend.weather import snapshot
from backend.radar import encode
from weather_fixture import weather_fixture
from radar_fixture import radar_fixture
from PIL import Image
from io import BytesIO
live=snapshot(weather_fixture(),datetime(2026,9,10,14,30))
h=Harness();h.file=live;h.m[0x9804]=2;h.run(13,0xa003)
assert h.m[0x9805]==3 and h.m[0x980c]==1 and h.m[0x9840]==70
for page in range(11):
 h.m[0x9800]=page;h.run(0,'p8b_main:p8s_redraw');assert h.m[0]==0
for offset in (15,33,34,42,44,50,51,54,55,354,355,633,634,872):
 bad=bytearray(live);bad[offset]=255;bad[8:10]=((sum(bad[6:8])+sum(bad[10:]))&65535).to_bytes(2,'little')
 h.file=bytes(bad);before=bytes(h.m[0x6000:0x6400]);h.run(13,0xa003)
 assert bytes(h.m[0x6000:0x6400])==before and h.m[0x9805]==2,offset
# Country observations, labels and map commit together; US radar is disabled in PH.
from backend.countries import PHILIPPINES
ph=snapshot(weather_fixture(),datetime(2026,9,10,14,30),cities=PHILIPPINES,country=1)
h.file=ph;h.run(13,0xa003);assert h.m[0x981e]==1
for page in (0,1,2,4):
 h.m[0x9800]=page;h.run(0,'p8b_main:p8s_redraw');assert h.m[0]==0
 if page==1:assert h.text(19,12,6)==b'BAGUIO' and h.text(49,32,5)==b'DAVAO'
 if page==4:
  # Philippine geography remains even with no live or demo radar loaded.
  base=0x1b000 if h.m[0x9809] else 0xc000
  assert h.m.vram[base+14*256+34*2:base+14*256+34*2+2]==h.m.banks[31][(2*42+16)*2:(2*42+17)*2]
h.m[0x980e]=1;h.run(15,0xa003);assert h.m[0x980e]==0
h.m[0x9820]=3;h.m[0x981f]=0
h.run(13,0xa003);assert h.m[0x9805]==2 and h.m[0x981e]==1
h.file=live;h.run(13,0xa003);assert h.m[0x981e]==0
h.m[0x9820]=0
# Expired data is never reported as fresh online weather.
h.hour=15;h.file=live;h.run(13,0xa003);assert h.m[0x9805]==2
h.hour=14;h.file=live;h.run(13,0xa003)
pic=Image.new('RGB',(600,392),'navy');buf=BytesIO();pic.save(buf,format='GIF')
h.radar=encode(buf.getvalue(),datetime(2026,9,10,14,30));h.m.writes.clear();h.run(15,0xa003)
assert h.m[0x980e]==1 and set(h.m.writes)==set(range(0x12020,0x13a00))
h.m[0x9800]=4;h.run(0,'p8b_main:p8s_redraw')
# Aging must also hide old radar when automatic fetching is disabled.
h.hour=15;h.run(0,'p8b_main:p8s_clock_draw');assert h.m[0x980e]==0
h.hour=14;h.run(15,0xa003);assert h.m[0x980e]==1
h.radar=h.radar[:-1];h.run(15,0xa003);assert h.m[0x980e]==0 and h.m[0x9821]==1
# Offline demos cannot become live by being renamed WCRLIVE.BIN.
h.radar=radar_fixture(stamp=datetime(2026,9,10,14,30),demo=True)
h.run(15,0xa003);assert h.m[0x980e]==0 and h.m[0x9821]==1
h.radar=radar_fixture(stamp=datetime(2026,9,10,14,30));h.run(15,0xa003)
assert h.m[0x980e]==1 and h.m[0x9821]==0
h.m[0x981e]=1;h.run(15,0xa003);assert h.m[0x980e]==0 and h.m[0x9821]==1
h.radar=radar_fixture(1,datetime(2026,9,10,14,10));h.run(15,0xa003)
assert h.m[0x980e]==1 and h.m[0x9821]==0
h.m[0x981e]=0;h.radar=None;h.run(15,0xa003)

# Fresh observations survive midnight, month/year changes and leap day.
for clock,stamp in [([126,9,11,0,5,0,0,4],datetime(2026,9,10,23,55)),
                    ([127,1,1,0,5,0,0,4],datetime(2026,12,31,23,55)),
                    ([128,3,1,0,5,0,0,4],datetime(2028,2,29,23,55)),
                    ([127,3,1,0,5,0,0,4],datetime(2027,2,28,23,55))]:
 h.clock=clock;h.radar=radar_fixture(stamp=stamp);h.run(15,0xa003)
 assert h.m[0x980e]==1 and not h.m[0x9821],(clock,stamp)
h.clock=None;h.radar=None;h.run(15,0xa003)
# Full compiled UART path: detect, scan, select, join, clear secret, stream data.
h.m.uart=True;h.m[0x69c0]=1;h.run(12,0xa003)
assert h.m[0x694b]==2 and b'ATW10' in h.m.commands
h.m[0x981a]=1;h.m[0x69c2]=13;h.run(14,0xa006)
assert bytes(h.m[0x6950:0x695d])==b'Home Network\0' and h.m[0x69c1]==2
for key in (65,0xc2,51):h.m[0x69c2]=key;h.run(14,0xa006)
assert bytes(h.m[0x6980:0x6984])==b'aB3\0'
h.m[0x69c0]=3;h.run(12,0xa003)
assert b'ATW"Home Network,aB3"' in h.m.commands
assert not any(h.m[0x6980:0x69c0]) and h.m[0x69c5]==3
url=b'http://weather.local:8767\0';h.m[0x6a00:0x6a00+len(url)]=url
h.m.wire=live;h.run(12,0xa006)
assert h.m[0x6a87]==1 and bytes(h.m[0x6400:0x6800])==live
assert h.m[0x6a84]+256*h.m[0x6a85]==1024
# A stale SD radar cannot shadow a fresh modem response after connecting.
h.radar=b'corrupt SD radar';h.m.wire=radar_fixture(stamp=datetime(2026,9,10,14,30))
h.run(15,0xa003,budget=8_000_000)
assert h.m[0x980e]==1 and not h.m[0x9821]
assert b'/x16/radar.hex' in h.m.commands[-1]
# A failed connection cannot make a recent SD cache appear to be a live feed.
h.radar=radar_fixture(stamp=datetime(2026,9,10,14,30));h.m.wire=b'bad radar'
h.run(15,0xa003);assert not h.m[0x980e] and h.m[0x9821]
# The city request traverses the real modem encoder and bounded receiver.
city_request=bytes(range(64));h.m[0x6b00:0x6b40]=city_request
h.m.wire=bytes(range(256));h.run(12,0xa00c)
assert h.m[0x6a87]==1 and bytes(h.m[0x6400:0x6500])==bytes(range(256))
assert b'/x16/city.hex?request='+city_request.hex().upper().encode() in h.m.commands[-1]
commands=len(h.m.commands)
h.m[0x6a00:0x6a80]=list(b'http://'+b'a'*119+b'\0\0');h.run(12,0xa00c)
assert len(h.m.commands)==commands and not h.m[0x6a87]
h.m[0x6a00:0x6a80]=list(url.ljust(128,b'\0'))
# A larger response must not escape the caller's bounded staging area.
h.m[0x6800]=0xa5;h.m.wire=live+b'x';h.run(12,0xa006)
assert h.m[0x6a87]==0 and h.m[0x6800]==0xa5
h.m[0x9800]=10;h.m[0x981a]=0;h.m[0x69c1]=0;h.m[0x6980]=65;h.key(27)
assert h.m[0x9800]==7 and not any(h.m[0x6980:0x69c0])
# Settings mouse navigation opens the full-page setup screen.
h.word(0,'p8b_main:p8v_mx',200);h.word(0,'p8b_main:p8v_my',120)
h.run(0,'p8b_main:p8s_handle_mouse');assert h.m[0x9800]==10
# Pointer routing and hit boundaries execute the actual compiled resident code.
def click(x,y):
 h.word(0,'p8b_main:p8v_mx',x);h.word(0,'p8b_main:p8v_my',y)
 h.run(0,'p8b_main:p8s_handle_mouse')
def hit(page,x,y):
 h.m[0x9800]=page
 h.m[0x9810:0x9814]=[x&255,x>>8,y&255,y>>8]
 if page==10:h.run(14,0xa00c)
 elif page==11:h.run(17,0xa009)
 else:h.run(0,'p8b_interaction:p8s_resolve')
 return h.m[0x9818],h.m[0x9819]
for page in range(9):
 assert hit(0,60,80+24*page)==(2,page)
 assert hit(0,60,103+24*page)==(2,page)
 h.m[0x9800]=0;click(60,92+24*page);assert h.m[0x9800]==page
assert hit(0,60,296)==(0,0)
assert hit(0,320,332)==(2,11) and hit(0,471,347)==(2,11)
assert hit(0,319,340)==(0,0) and hit(0,472,340)==(0,0)
assert hit(11,220,140)==(7,1) and hit(11,220,170)==(7,2)
assert hit(11,400,170)==(7,3)
for x,page in [(40,9),(160,6),(260,5),(370,4),(480,7)]:
 h.m[0x9800]=0;click(x,460);assert h.m[0x9800]==page
assert hit(0,580,460)==(1,27)
for city in range(10):
 x=24 if city<5 else 256;y=352+city%5*16
 h.m[0x9800]=0;click(x,y);assert h.m[0x9801]==city
 assert hit(0,x,y+15)==(3,city)
for x in (0,244,472):assert hit(0,x,356)==(0,0)
for x,y,city in [(172,116,7),(164,180,9),(196,228,2),(260,172,6),(324,140,3),(292,244,4),(404,184,1),(420,116,8),(404,276,5)]:
 h.m[0x9800]=1;click(x,y);assert (h.m[0x9800],h.m[0x9801])==(3,city)
h.m[0x981e]=1
for x,y,city in [(156,148,1),(156,108,2),(396,156,3),(156,228,4),(156,188,5),(396,204,6),(396,108,7),(396,268,8),(156,268,9)]:
 h.m[0x9800]=1;click(x,y);assert (h.m[0x9800],h.m[0x9801])==(3,city)
h.m[0x981e]=0
for y,city in [(130,3),(194,6),(258,4)]:
 h.m[0x9800]=2;click(260,y);assert (h.m[0x9800],h.m[0x9801])==(3,city)
for page in (3,6):
 h.m[0x9800]=page;h.m[0x9801]=0;click(200,320);assert h.m[0x9801]==9
 click(420,320);assert h.m[0x9801]==0
 click(300,320);assert h.m[0x9800]==5
h.m[0x980c]=1;h.m[0x9800]=5
click(420,120);assert h.m[0x9814]==1
click(210,120);assert h.m[0x9814]==0
for y,key in [(120,87),(164,85),(196,84),(228,65),(260,68),(288,67),(316,83)]:
 assert hit(7,200,y)==(1,key)
assert hit(8,300,320)==(2,9)
for y,target in [(160,3),(228,5),(252,7),(276,82)]:
 assert hit(9,250,y)==(1 if target==82 else 2,target)
# Guided setup: choices, bounded network selection, fields, back/close, and IP normalization.
h.m[0x981a]=0
assert hit(10,200,180)==(5,0)
assert hit(10,200,280)==(6,0)
h.m[0x981a]=1;h.m[0x694b]=2;h.m[0x694c]=0
h.m[0x9800]=10;click(100,240);assert h.m[0x694c]==0 and h.m[0x981a]==1
click(100,184);assert h.m[0x694c]==1 and h.m[0x981a]==2 and h.m[0x69c1]==2
for y,focus in [(184,1),(232,2)]:
 click(200,y);assert h.m[0x69c1]==focus
for x,y in [(620,184),(620,232),(16,250)]:assert hit(10,x,y)==(0,0)
# Tab from a non-editing password step chooses SSID, never the weather URL.
h.m[0x69c1]=0;h.m[0x69c2]=9;h.run(14,0xa006);assert h.m[0x69c1]==1
h.m[0x6980]=65;click(110,444);assert h.m[0x981a]==1 and not any(h.m[0x6980:0x69c0])
h.m[0x981a]=3;h.m[0x981b]=0
assert hit(10,200,256)==(3,3)
for raw,expected in [(b'192.168.1.20',b'http://192.168.1.20:8767'),(b'weather.local:9000',b'http://weather.local:9000'),(b'http://192.168.1.20:8767/',b'http://192.168.1.20:8767')]:
 h.m[0x6a00:0x6a80]=list(raw)+[0]*(128-len(raw))
 h.run(14,'p8b_wifi:p8s_normalize_address')
 assert bytes(h.m[0x6a00:0x6a00+len(expected)+1])==expected+b'\0'
h.m[0x9800]=10;click(560,80);assert h.m[0x9800]==7 and h.m[0x981a]==0
# The computer path checks the real provider and reaches the ready screen.
h.file=live;h.hour=14;h.m[0x9800]=10;h.m[0x981a]=0;click(200,180)
assert h.m[0x981a]==4 and h.m[0x9805]==3
assert hit(10,450,444)==(4,0)
click(560,80);assert h.m[0x9800]==7
# Computer setup never probes the modem, even when an old bridge URL is saved.
h.file=None;h.radar=None;h.m[0x9800]=10;h.m[0x981a]=0;before=len(h.m.commands)
click(200,180);assert len(h.m.commands)==before and h.m[0x981a]==3
h.key(88);assert h.m[0x9800]==7
# Scenery is clickable, rotates independently, and wraps across tick rollover.
h.m[0x9800]=0;h.m[0x9816]=0;click(550,380);assert h.m[0x9816]==1
h.m[0x9808]=0;h.word(0,'p8b_main:p8v_last_scene',65000);h.ticks=(65000+1800)&65535
h.run(0,'p8b_main:p8s_service_timers');assert h.m[0x9816]==2
# Half-glyph padding centers the nav bar within one pixel of the seven-pixel text.
font=(ROOT/'dist/sdcard/WCFONT.BIN').read_bytes()
assert 704*32<len(font)<=1024*32
assert font[188*32:189*32]==bytes(16)+bytes([0x22])*16
assert font[189*32:190*32]==bytes([0x22])*16+bytes(16)
assert len((ROOT/'dist/sdcard/WCPOINTER.BIN').read_bytes())==1024

join_failure_check()
asset=json.loads((ROOT/'build/assets.json').read_text());assert asset['tiles']<=628
regions=[asset['vram'][name] for name in ('art_tiles','header','scenery','font','text_map_a','text_map_b','pointer','palette')]
for i,(start,end) in enumerate(regions):
 assert start<end<=0x20000
 for other_start,other_end in regions[i+1:]:assert end<=other_start or other_end<=start
print('PASS: sixteen compiled banks, resident shell, all twelve views, bank restoration,')
print('      RTC station transitions, isolated panel writes, keyboard routing, city wrap,')
print('      signed temperatures, units/settings, bounded snapshots and failure preservation,')
print('      minute refresh/manual mode/timer rollover, and RAM/VERA budgets.')
print('      Live weather validation/staleness, bounded NOAA tiles, Wi-Fi scan/join,')
print('      password case and clearing, UART transfer bounds, complete mouse routing,')
print('      pixel-checked centered bars on every view, nonoverlapping text buffers,')
print('      independent scenery rotation and all 28 scene banks.')
