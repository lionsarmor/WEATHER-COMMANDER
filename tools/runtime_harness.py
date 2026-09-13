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
  self.files={name:(ROOT/'dist/sdcard'/name).read_bytes() for name in ('WCDMUS.BIN','WCDMPH.BIN','WCRDEMO.BIN','WCRDPH.BIN')}
  self.readers={};self.writer=None;self.write_ok=True
  for bank,symbols in self.symbols.items():
   if 'cbm:RDTIM16' in symbols:self.hook(bank,'cbm:RDTIM16',lambda:self.ay(self.ticks))
   if 'diskio:f_open' in symbols:self.hook(bank,'diskio:f_open',lambda b=bank:self.open_file(b))
   if 'diskio:f_close' in symbols:self.hook(bank,'diskio:f_close',lambda:None)
   if 'diskio:f_read' in symbols:self.hook(bank,'diskio:f_read',lambda b=bank:self.read_file(b))
   if 'diskio:f_open_w' in symbols:self.hook(bank,'diskio:f_open_w',self.open_write)
   if 'diskio:f_close_w' in symbols:self.hook(bank,'diskio:f_close_w',lambda:None)
   if 'diskio:f_write' in symbols:self.hook(bank,'diskio:f_write',lambda b=bank:self.write_file(b))
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
 def cstring(self,address):
  result=bytearray()
  while self.m[address]:result.append(self.m[address]);address+=1
  return result.decode('ascii')
 def open_file(self,bank):
  name=self.cstring(self.cpu.a+self.cpu.y*256)
  self.readers[bank]=(self.files.get(name),0)
  self.ay(int(name in self.files))
 def read_file(self,bank):
  sym=self.symbols[bank];p=sym['diskio:f_read:bufferpointer'];n=sym['diskio:f_read:num_bytes']
  addr=self.m[p]+self.m[p+1]*256;size=self.m[n]+self.m[n+1]*256
  data,offset=self.readers.get(bank,(None,0));raw=(data or b'')[offset:offset+size]
  self.m[addr:addr+len(raw)]=raw;self.readers[bank]=(data,offset+len(raw));self.ay(len(raw))
 def open_write(self):
  self.writer=self.cstring(self.cpu.a+self.cpu.y*256).removeprefix('@:')
  if self.write_ok:self.files[self.writer]=b''
  self.ay(int(self.write_ok))
 def write_file(self,bank):
  sym=self.symbols[bank];p=sym['diskio:f_write:bufferpointer'];n=sym['diskio:f_write:num_bytes']
  addr=self.m[p]+self.m[p+1]*256;size=self.m[n]+self.m[n+1]*256
  if self.write_ok:self.files[self.writer]+=bytes(self.m[addr:addr+size])
  self.ay(int(self.write_ok))
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
   if pc in (0xff74,0xff77):
    pointer=self.cpu.a if pc==0xff74 else self.m[0x3b2]
    target=self.m[pointer]+256*self.m[pointer+1]+self.cpu.y
    if pc==0xff74:self.cpu.a=self.m.banks[self.cpu.x][target-0xa000];self.cpu.FlagsNZ(self.cpu.a)
    else:self.m.banks[self.cpu.x][target-0xa000]=self.cpu.a
    self.cpu.pc=self.cpu.stPopWord()+1;continue
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
