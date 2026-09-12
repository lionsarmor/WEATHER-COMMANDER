"""Small pixel postcards and Natural Earth island geography for layer one."""
import struct, sys
from PIL import Image, ImageDraw

def build(root,out,glyphs):
 atlas={};start=len(glyphs)//32
 def encode(pic,name):
  result=bytearray()
  for y in range(0,224,8):
   for x in range(0,336,8):
    raw=bytes(pic.crop((x,y,x+8,y+8)).getdata())
    if not any(raw):tile=256
    else:
     if raw not in atlas:
      atlas[raw]=len(glyphs)//32
      glyphs.extend(bytes((raw[i]<<4)|raw[i+1] for i in range(0,64,2)))
      cell=Image.frombytes('P',(8,8),raw)
      for method,flag in [(Image.Transpose.FLIP_LEFT_RIGHT,1024),(Image.Transpose.FLIP_TOP_BOTTOM,2048),(Image.Transpose.ROTATE_180,3072)]:
       atlas.setdefault(bytes(cell.transpose(method).getdata()),atlas[raw]|flag)
     tile=atlas[raw]
    result.extend(struct.pack('<H',tile))
  (out/name).write_bytes(result)
 # Cards are x20..37 and x40..57 on screen. Art occupies y16..24.
 home=Image.new('P',(336,224));d=ImageDraw.Draw(home)
 for x,ph in [(16,False),(176,True)]:
  y=32
  d.rectangle((x,y,x+143,y+71),fill=3)
  d.rectangle((x,y+44,x+143,y+71),fill=2)
  if not ph:
   d.ellipse((x+112,y+5,x+126,y+19),fill=5)
   d.ellipse((x+116,y+2,x+129,y+15),fill=3)
   for sx,sy in [(9,8),(38,12),(73,5),(103,24)]:d.point((x+sx,y+sy),fill=6)
   for bx,bw,bh in [(4,15,20),(23,17,31),(45,13,22),(64,19,39),(87,13,27),(106,14,18),(124,17,29)]:
    d.rectangle((x+bx,y+44-bh,x+bx+bw,y+46),fill=1)
    for wy in range(y+47-bh,y+42,6):
     for wx in range(x+bx+3,x+bx+bw-1,5):d.rectangle((wx,wy,wx+1,wy+2),fill=5)
    for wy in range(y+51,y+min(70,50+bh//2),5):d.line((x+bx+3,wy,x+bx+bw-2,wy),fill=3 if wy%2 else 4)
  else:
   d.ellipse((x+102,y+6,x+122,y+26),fill=5)
   d.polygon([(x,y+46),(x+29,y+22),(x+48,y+42),(x+71,y+14),(x+99,y+46)],fill=7)
   d.polygon([(x+53,y+34),(x+71,y+14),(x+90,y+36),(x+70,y+27)],fill=8)
   d.polygon([(x+70,y+58),(x+143,y+45),(x+143,y+71),(x+31,y+71)],fill=5)
   d.line((x+113,y+60,x+119,y+31),fill=13,width=3)
   for pts in [[(119,32),(106,24),(99,28)],[(119,32),(128,23),(137,25)],[(119,32),(104,34),(100,42)],[(119,32),(130,33),(135,40)]]:
    d.line([(x+a,y+b) for a,b in pts],fill=8,width=3)
   for wx,wy in [(9,52),(31,61),(60,51),(5,66)]:d.line((x+wx,y+wy,x+wx+13,y+wy),fill=4)
 for x in (16,176):
  card=home.crop((x,32,x+144,104)).resize((112,48),Image.Resampling.NEAREST)
  d.rectangle((x,32,x+143,103),fill=2)
  home.paste(card,(x+16,48))
 encode(home,'WCHART.BIN')
 # Equirectangular map at the country's latitude: true island outlines, north up.
 sys.path.insert(0,str(root))
 from backend.maps import philippines,project
 pic=philippines();d=ImageDraw.Draw(pic)
 # Leader lines terminate beside labels in the ocean, leaving islands readable.
 stations=[(120.9842,14.5995,88,64),(120.596,16.4023,88,24),
           (123.7438,13.1391,240,72),(118.7353,9.7392,88,144),
           (122.5621,10.7202,88,104),(123.8854,10.3157,240,120),
           (124.9617,11.2543,240,24),(125.4553,7.1907,240,184),
           (122.079,6.9214,88,184)]
 for lon,lat,tx,ty in stations:
  px,py=project(lon,lat);d.line([(tx,ty),(px,ty),(px,py)],fill=4)
  d.rectangle((px-1,py-1,px+1,py+1),fill=5)
 encode(pic,'WCPH.BIN')
 if len(glyphs)>1024*32:raise ValueError(f'Country artwork exceeds font atlas: {len(glyphs)//32} tiles')
 print(f'Country artwork: {len(glyphs)//32-start} tiles; font atlas {len(glyphs)//32}/1024')
