"""Hand-drawn, bank-sized pixel postcards inspired by weather television."""
import random
from PIL import Image, ImageDraw

THEMES=('BRIGHTER DAYS','COUNTRY ROAD','ALPINE LAKE','PALM BEACH','RED ROCKS','LIGHTHOUSE','NEON HIGHWAY')
BAYER=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))


def scene(phase,theme,text):
 rng=random.Random(841+theme)
 im=Image.new('P',(152,80),1);d=ImageDraw.Draw(im)
 night=phase==3
 # Broad cobalt/violet/rose bands, with texture confined to their edges.
 for y in range(68):
  lo,hi,start=(3,11,23) if y<37 else (11,10,42)
  level=max(0,min(16,(y-start)*8))
  for x in range(152):
   im.putpixel((x,y),hi if BAYER[y%4][x%4]<level else lo)
  if y<37 and y%4==0:
   for x in range((y*3)%17,152,29):d.line((x,y,x+10,y),fill=3)
 sky=im.copy()
 if phase!=1:
  for _ in range(46 if night else 17):
   x,y=rng.randrange(152),rng.randrange(30)
   d.point((x,y),fill=6 if rng.random()<.3 else 14)
  if night:
   d.ellipse((124,3,137,18),fill=15)
   # Restore the sky inside the crescent, avoiding a dark rectangular cutout.
   for y in range(2,16):
    for x in range(128,141):
     if ((x-134)/7)**2+((y-8)/8)**2<=1:im.putpixel((x,y),sky.getpixel((x,y)))
 if not night:
  sy=(29,7,31)[phase]
  d.ellipse((113,sy,132,sy+19),fill=15)
  if phase!=1:
   for y in range(sy+10,sy+20,3):
    for x in range(112,134):im.putpixel((x,y),sky.getpixel((x,y)))
  for x,y,w in [(8,12,23),(45,22,18),(86,8,13)]:
   d.line((x,y,x+w,y),fill=6)
   d.line((x+4,y-1,x+w-4,y-1),fill=10 if phase!=1 else 6)
   d.line((x+9,y-2,x+w-7,y-2),fill=6)

 def tree(x,y,size=14):
  d.line((x,y,x,y+size+5),fill=1)
  for offset,width in [(0,3),(4,5),(8,7)]:
   width=max(2,width*size//14)
   d.polygon([(x,y+offset),(x-width,y+offset+size//2),(x+width,y+offset+size//2)],fill=1 if night else 7)
   if not night:d.line((x,y+offset+1,x-width+1,y+offset+size//2-1),fill=8)

 def water(y):
  # Reflect actual shapes above the shoreline in broken, rippling columns.
  shore=im.copy()
  d.rectangle((0,y,151,67),fill=2)
  for yy in range(y+1,68):
   if (yy-y)%3==0:continue
   source=max(0,y-1-(yy-y)*2)
   shift=(0,1,-1,2)[yy%4]
   for x in range(152):
    color=shore.getpixel((max(0,min(151,x+shift)),source))
    if color in (5,15):
     if rng.random()>.28:im.putpixel((x,yy),5 if (yy-y)<8 else 9)
    elif color in (4,6):im.putpixel((x,yy),4 if rng.random()>.4 else 3)
    elif color!=1 and (x//7+yy//2)%3==0:im.putpixel((x,yy),3 if yy%2 else 11)
  for yy in range(y+2,68,4):
   for xx in range((yy*7)%19,152,27):d.line((xx,yy,xx+rng.randrange(2,8),yy),fill=4 if phase==1 else 14)

 def grass(box,count=80):
  x0,y0,x1,y1=box
  for _ in range(count):
   x,y=rng.randrange(x0,x1),rng.randrange(y0,y1)
   d.line((x,y,x+rng.randrange(1,3),y),fill=rng.choice((7,8,9) if not night else (7,8,14)))

 if theme==0:
  # The reference city's crowned tower, stepped roofs, gold windows and river.
  for x in range(0,152,7):
   top=rng.randrange(37,48)
   d.rectangle((x,top,x+5,52),fill=14)
   if x%3==0:d.point((x+2,top+3),fill=13)
  buildings=[(0,39,9),(13,31,12),(29,36,9),(40,20,13),(58,41,14),
             (76,11,17),(97,42,8),(107,25,12),(123,34,12),(141,42,10)]
  for i,(x,top,w) in enumerate(buildings):
   d.rectangle((x,top,x+w,52),fill=1)
   if i==5:
    d.rectangle((x+3,top-4,x+w-3,top),fill=1)
    d.rectangle((x+6,top-6,x+w-6,top),fill=1)
    d.line((x+7,top-3,x+10,top-3),fill=3)
   elif i in (1,3):
    d.rectangle((x+w//2,top-4,x+w-1,top),fill=1)
    if i==3:d.point((x+w//2+1,top-5),fill=13)
   for wx in range(x+3,x+w-1,4):
    for wy in range(top+4,51,5):
     color=5 if rng.random()>.22 else 14
     d.rectangle((wx,wy,wx+1,wy+2),fill=color)
  d.line((0,53,151,53),fill=4)
  for x in range(3,152,10):d.line((x,52,x+2,52),fill=5)
  water(54)
  for x in (18,44,81,88,113,130):
   for y in range(56,67,3):d.line((x+(y%2),y,x+1+(y%2),y),fill=5 if y<62 else 14)

 elif theme==1:
  d.polygon([(0,40),(19,26),(37,34),(60,27),(86,38),(113,24),(151,38),(151,67),(0,67)],fill=14)
  d.polygon([(0,45),(26,36),(63,46),(106,34),(151,45),(151,67),(0,67)],fill=7)
  d.polygon([(0,53),(45,45),(77,50),(115,43),(151,49),(151,67),(0,67)],fill=8)
  grass((0,49,152,68),150)
  d.polygon([(91,42),(94,42),(76,51),(81,56),(108,67),(70,67),(62,56),(66,50)],fill=9)
  d.line([(90,44),(69,51),(68,55),(84,67)],fill=14)
  # Clapboard farmhouse and barn, porch, chimney and picket fence.
  d.rectangle((29,35,61,51),fill=9)
  for y in range(38,52,3):d.line((29,y,61,y),fill=13)
  d.polygon([(25,36),(45,23),(66,36)],fill=1)
  d.line((27,35,45,24,63,35),fill=14)
  d.rectangle((34,24,37,31),fill=14)
  for x in (33,51):
   d.rectangle((x,39,x+5,44),fill=5);d.line((x+2,39,x+2,44),fill=1)
  d.rectangle((43,41,47,51),fill=1)
  d.line((27,48,64,48),fill=6)
  for x in (28,63):d.line((x,39,x,52),fill=6)
  d.rectangle((115,38,133,49),fill=13);d.polygon([(112,38),(124,29),(136,38)],fill=1)
  d.rectangle((121,41,127,49),fill=1)
  for x,y in [(9,32),(102,31),(146,31)]:tree(x,y,15)
  for x in range(0,60,7):
   d.line((x,54,x,62),fill=6);d.line((x,56,x+7,55),fill=9);d.line((x,59,x+7,58),fill=9)
  for x,y in [(113,57),(136,60),(24,64),(121,64)]:d.point((x,y),fill=5)

 elif theme==2:
  d.polygon([(0,41),(23,19),(43,37),(77,4),(105,36),(130,16),(151,37),(151,54),(0,54)],fill=14)
  for x,y,w in [(23,19,17),(77,4,26),(130,16,20)]:
   d.polygon([(x,y),(x-w,y+w),(x-5,y+w-7),(x,y+w-3),(x+3,y+w-12),(x+w,y+w)],fill=6)
   d.polygon([(x,y+2),(x+3,y+w-12),(x+w,y+w),(x+7,y+w-2)],fill=9)
   d.line((x-1,y+5,x-8,y+17),fill=14)
  d.polygon([(0,42),(16,34),(34,43),(51,35),(68,46),(112,32),(151,43),(151,56),(0,56)],fill=7)
  for x in range(0,152,8):tree(x,40+rng.randrange(5),7)
  water(49)
  d.polygon([(0,54),(15,57),(35,67),(0,67)],fill=1)
  d.polygon([(151,51),(140,56),(129,67),(151,67)],fill=1)
  for x,y in [(5,37),(17,44),(146,33),(134,44)]:tree(x,y,16)
  d.polygon([(52,60),(66,60),(63,63),(56,63)],fill=13)
  d.line((59,58,64,64),fill=9)
  d.line((24,63,30,65),fill=14);d.line((139,60,146,58),fill=14)

 elif theme==3:
  d.polygon([(87,40),(109,32),(126,34),(145,29),(151,33),(151,46),(87,46)],fill=14)
  water(42)
  d.polygon([(0,52),(29,54),(57,61),(97,62),(127,55),(151,53),(151,67),(0,67)],fill=9)
  d.line([(0,51),(28,53),(58,60),(97,61),(128,54),(151,52)],fill=6)
  for x,y in [(19,59),(43,62),(100,65),(133,59),(144,63)]:d.line((x,y,x+4,y),fill=13)
  for x,top in [(17,23),(37,32)]:
   d.line([(x-5,62),(x-3,47),(x,top)],fill=1,width=2)
   d.line((x-4,58,x-2,48),fill=13)
   for dx,dy in [(-16,3),(-13,-5),(-5,-10),(9,-9),(17,-2),(12,7)]:
    d.line([(x,top),(x+dx//2,top+dy-2),(x+dx,top+dy)],fill=7 if phase==1 else 1,width=2)
    d.point((x+dx,top+dy+2),fill=8)
  d.line((115,46,115,62),fill=1)
  d.pieslice((101,36,129,56),180,360,fill=12)
  d.polygon([(115,36),(109,46),(121,46)],fill=6)
  d.line((105,63,113,58,122,61),fill=6)
  d.line((74,30,74,45),fill=6)
  d.polygon([(76,31),(76,41),(86,41)],fill=6)
  d.polygon([(72,35),(66,42),(72,42)],fill=9)
  d.polygon([(65,45),(88,45),(82,48),(70,48)],fill=1)
  for x in (65,77,83):d.line((x,50,x+3,50),fill=4)

 elif theme==4:
  d.polygon([(0,38),(17,30),(31,36),(52,25),(71,33),(93,23),(120,35),(151,28),(151,67),(0,67)],fill=14)
  d.polygon([(0,48),(9,44),(17,24),(35,24),(44,45),(68,44),(79,17),(96,17),(105,40),(123,43),(139,31),(151,31),(151,67),(0,67)],fill=13)
  for x,top,w in [(17,24,18),(79,17,17),(139,31,12)]:
   d.polygon([(x+w-4,top),(x+w,top),(x+w+9,top+27),(x+w-1,top+25)],fill=12)
   for yy in range(top+5,top+25,4):
    d.line((x-2,yy,x+w,yy),fill=9 if yy%3 else 12)
   d.line((x+3,top+2,x,top+15),fill=9)
  d.polygon([(0,55),(49,46),(84,54),(124,47),(151,51),(151,67),(0,67)],fill=9)
  grass((0,55,152,68),110)
  d.polygon([(86,46),(89,46),(72,58),(66,67),(39,67),(59,56)],fill=1)
  d.line([(85,47),(61,57),(43,67)],fill=13)
  for x,y in [(81,50),(70,56),(58,64)]:d.line((x,y,x-2,y+2),fill=5)
  for x,y in [(17,44),(123,43),(143,53)]:
   d.line((x,y-9,x,y+13),fill=7,width=3)
   d.line((x-6,y-5,x-6,y+2,x,y+2),fill=7,width=3)
   d.line((x+5,y-6,x+5,y-1,x,y-1),fill=7,width=3)
   d.line((x-1,y-7,x-1,y+10),fill=8)
  for x,y in [(32,61),(101,59),(117,65)]:
   d.line((x-2,y,x+3,y),fill=13);d.point((x,y-2),fill=7)

 elif theme==5:
  d.polygon([(101,41),(126,34),(151,38),(151,47),(101,47)],fill=14)
  water(43)
  d.polygon([(0,43),(24,40),(42,48),(48,56),(69,67),(0,67)],fill=7)
  d.polygon([(0,53),(23,48),(40,52),(46,59),(62,67),(0,67)],fill=14)
  for x,y in [(4,53),(18,51),(28,55),(40,59),(46,64),(10,62)]:
   d.polygon([(x,y),(x+6,y-2),(x+10,y+3),(x+2,y+4)],fill=1)
   d.line((x,y,x+6,y-2),fill=9)
  d.line([(40,51),(46,54),(51,60),(65,66)],fill=6)
  d.polygon([(18,43),(23,18),(32,18),(37,43)],fill=6)
  d.polygon([(30,19),(32,19),(37,43),(32,43)],fill=9)
  d.polygon([(21,29),(34,29),(35,34),(20,34)],fill=13)
  d.rectangle((22,14,33,19),fill=1)
  d.rectangle((24,15,31,17),fill=5)
  d.line((27,14,27,18),fill=1)
  d.polygon([(20,14),(27,8),(35,14)],fill=1)
  d.line((27,6,27,9),fill=14)
  d.rectangle((26,38,29,43),fill=1)
  if phase!=1:
   d.line((34,15,92,11),fill=5);d.line((34,17,100,23),fill=9)
   for x in range(38,95,3):d.point((x,17),fill=5)
  d.rectangle((4,41,16,47),fill=6);d.polygon([(2,41),(10,35),(18,41)],fill=13)
  d.line((108,40,108,53),fill=6)
  d.polygon([(110,41),(110,49),(119,49)],fill=9)
  d.polygon([(100,53),(122,53),(116,57),(105,57)],fill=1)
  for x,y in [(66,32),(92,28)]:d.line((x,y,x+2,y+1,x+4,y),fill=6)

 elif theme==6:
  # Synthwave skyline, perspective grid, palms and a detailed low-slung coupe.
  for x in range(0,152,8):
   top=32+rng.randrange(11)
   d.rectangle((x,top,x+6,46),fill=1)
   if x%3==0:d.line((x+2,top+3,x+2,top+6),fill=12)
  d.rectangle((0,47,151,67),fill=2)
  for x in range(-130,290,24):d.line((76,45,x,67),fill=11)
  for y in (48,51,55,60,67):d.line((0,y,151,y),fill=12)
  d.polygon([(69,45),(82,45),(112,67),(38,67)],fill=1)
  d.line((68,45,36,67),fill=4);d.line((83,45,114,67),fill=4)
  d.line((67,45,33,67),fill=11);d.line((84,45,117,67),fill=11)
  for y,w in [(49,0),(54,1),(62,2)]:d.rectangle((75-w,y,76+w,y+2),fill=5)
  for x,top in [(18,31),(140,28)]:
   d.line((x,top,x-3,57),fill=1,width=2)
   for dx,dy in [(-12,-2),(-7,-7),(7,-6),(11,0)]:d.line((x,top,x+dx,top+dy),fill=1,width=2)
  d.polygon([(89,53),(101,53),(105,57),(108,59),(107,64),(83,64),(82,59),(86,57)],fill=14)
  d.polygon([(90,54),(99,54),(102,57),(87,57)],fill=2)
  d.line((84,58,106,58),fill=12)
  d.rectangle((83,60,108,64),fill=1)
  d.line((85,61,91,61),fill=13,width=2);d.line((99,61,105,61),fill=13,width=2)
  d.line((94,63,97,63),fill=6)
  d.line((85,66,92,66),fill=12);d.line((99,66,106,66),fill=12)

 # Keep the postcard caption legible against an unbroken dark strip.
 d.rectangle((0,69,151,79),fill=1)
 d.line((0,68,151,68),fill=4 if phase==1 else 11)
 label=('DAWN','DAY','DUSK','NIGHT')[phase]+' / '+THEMES[theme]
 text(im,(152-len(label)*6)//2,72,label,6)
 return im
