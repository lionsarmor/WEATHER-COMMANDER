"""NOAA precipitation-only overlay, projected onto the native Albers map.

Never downsample a screenshot: the basemap and labels stay native-resolution.
The bounded codebook preserves occupied quadrants when simplifying rare tiles.
"""
from collections import Counter
from datetime import datetime
from io import BytesIO
import json,struct,urllib.request,urllib.parse,colorsys
from PIL import Image
from .geometry import coordinate
SERVICE='https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer'
SIZE=16+207*32+42*28*2
LEVELS=(4,8,5,13,12,11,15)
BBOX=(-128,22,-65,52)

def intensity(pixel):
 r,g,b,a=pixel
 if a<128:return 0
 if min(r,g,b)>240:return 7
 if max(r,g,b)-min(r,g,b)<20:return 0
 h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
 if v<.15:return 0
 if h>.72:return 6
 if h<.055:return 5
 if h<.12:return 4
 if h<.20:return 3
 if h<.45:return 2
 return 1

def checksum(raw):return (sum(raw[4:12])+sum(raw[14:]))&65535

def configure(raw,country=0,demo=False):
 out=bytearray(raw);out[:4]=b'WCR4';out[5]=country;out[11]=int(demo)
 out[12:14]=checksum(out).to_bytes(2,'little')
 return bytes(out)

def fresh(raw,country=None,now=None):
 if not raw or len(raw)!=SIZE or raw[:4]!=b'WCR4':return False
 if raw[5] not in (0,1) or raw[11]!=0 or raw[14]!=0 or (country is not None and raw[5]!=country):return False
 if int.from_bytes(raw[12:14],'little')!=checksum(raw):return False
 try:stamp=datetime(1900+raw[6],*raw[7:11]).astimezone()
 except ValueError:return False
 age=((now or datetime.now().astimezone())-stamp).total_seconds()
 return 0<=age<=60*(30 if raw[5] else 15)

def pack_composite(picture,stamp,country):
 # Keep geography and echoes in the same tiles on X16's Philippines view.
 # If necessary, enlarge sample cells in place; never borrow another location.
 for step in (1,2,4,8):
  reduced=picture.copy()
  if step>1:
   for y in range(0,224,step):
    for x in range(0,336,step):
     pixels=list(picture.crop((x,y,x+step,y+step)).getdata())
     echoes=[p for p in pixels if p in LEVELS]
     color=max(echoes,key=LEVELS.index) if echoes else Counter(pixels).most_common(1)[0][0]
     reduced.paste(color,(x,y,x+step,y+step))
  tiles=[bytes(reduced.crop((x,y,x+8,y+8)).getdata()) for y in range(0,224,8) for x in range(0,336,8)]
  book=[bytes(64)]+[bytes([level])*64 for level in LEVELS]
  for tile in tiles:
   if tile not in book:book.append(tile)
  if len(book)<=207:break
 if len(book)>207:raise ValueError('Radar codebook limit')
 out=bytearray(SIZE);out[:4]=b'WCR4';out[4]=len(book)
 out[6:11]=bytes([stamp.year-1900,stamp.month,stamp.day,stamp.hour,stamp.minute])
 packed=bytes((t[p]<<4)|t[p+1] for t in book for p in range(0,64,2));out[16:16+len(packed)]=packed
 lookup={tile:i for i,tile in enumerate(book)}
 out[6640:]=b''.join(struct.pack('<H',0xf000|257+lookup[t]) for t in tiles)
 return configure(out,country=country)

def pack_overlay(picture,stamp):
 tiles=[bytes(picture.crop((x,y,x+8,y+8)).getdata()) for y in range(0,224,8) for x in range(0,336,8)]
 # Stable first entries are transparent + seven solid legend swatches.
 book=[bytes(64)]+[bytes([level])*64 for level in LEVELS]
 for mask in range(1,15):
  for level in LEVELS:
   book.append(bytes(level if mask&(1<<((y//4)*2+x//4)) else 0 for y in range(8) for x in range(8)))
 lookup={t:i for i,t in enumerate(book)}
 for tile,_ in Counter(tiles).most_common():
  if len(book)==207:break
  if tile not in lookup:lookup[tile]=len(book);book.append(tile)
 for tile in set(tiles)-lookup.keys():
  # Preserve which 4x4 quadrants contain returns; never substitute a storm
  # pattern from a different location, as nearest-tile screenshot encoding did.
  counts=Counter(p for p in tile if p);level=counts.most_common(1)[0][0] if counts else 0
  mask=0
  for q in range(4):
   if any(tile[y*8+x] for y in range(q//2*4,q//2*4+4) for x in range(q%2*4,q%2*4+4)):mask|=1<<q
  simplified=bytes(level if mask&(1<<((y//4)*2+x//4)) else 0 for y in range(8) for x in range(8))
  lookup[tile]=lookup[simplified]
 out=bytearray(SIZE);out[:4]=b'WCR4';out[4]=len(book)
 out[6:11]=bytes([stamp.year-1900,stamp.month,stamp.day,stamp.hour,stamp.minute])
 packed=bytes((t[p]<<4)|t[p+1] for t in book for p in range(0,64,2));out[16:16+len(packed)]=packed
 out[6640:]=b''.join(struct.pack('<H',0xf000|257+lookup[t]) for t in tiles)
 out[12:14]=checksum(out).to_bytes(2,'little')
 return bytes(out)

def encode(raw,stamp=None):
 image=Image.open(BytesIO(raw)).convert('RGBA')
 if image.width<2 or image.height<2:raise ValueError('Empty radar export')
 picture=Image.new('P',(336,224),0)
 # Two-pixel sampling keeps narrow bands visible; no interpolated fake colors.
 data=picture.load();source=image.load();west,south,east,north=BBOX
 for y in range(0,224,2):
  for x in range(0,336,2):
   lon,lat=coordinate(x+1,y+1)
   sx=int((lon-west)/(east-west)*image.width);sy=int((north-lat)/(north-south)*image.height)
   if not (0<=sx<image.width and 0<=sy<image.height):continue
   level=intensity(source[sx,sy])
   if level:
    color=LEVELS[level-1]
    for dy in (0,1):
     for dx in (0,1):data[x+dx,y+dy]=color
 return pack_overlay(picture,stamp or datetime.now().astimezone())

def request(path,params,limit):
 url=SERVICE+path+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':'Roddy-Weather-Commander/0.3'})
 with urllib.request.urlopen(req,timeout=20) as response:data=response.read(limit+1)
 if len(data)>limit:raise ValueError('Radar response exceeds limit')
 return data

def fetch_radar():
 # CONUS and overseas mosaics have different times: lock the actual CONUS
 # raster by ID instead of asking for the latest timestamp across the service.
 query=json.loads(request('/query',{'f':'json','where':"idp_subset='CONUS'",'outFields':'objectid,idp_validtime','returnGeometry':'false','orderByFields':'idp_validtime DESC','resultRecordCount':1},100_000))
 rows=query.get('features',[])
 if not rows:raise ValueError('NOAA CONUS raster is unavailable')
 entry=rows[0]['attributes'];stamp=datetime.fromtimestamp(entry['idp_validtime']/1000).astimezone()
 raw=request('/exportImage',{'f':'image','bbox':','.join(map(str,BBOX)),'bboxSR':4326,'imageSR':4326,'size':'756,360','format':'png32','interpolation':'RSP_NearestNeighbor','adjustAspectRatio':'false','mosaicRule':json.dumps({'mosaicMethod':'esriMosaicLockRaster','lockRasterIds':[entry['objectid']]})},2_000_000)
 return encode(raw,stamp)
