"""Public PAGASA/Panahon rain-rate feed, using its public embedded-map session.

The session/CSRF/signature headers follow the provider's shipped browser client.
No account, private key, or stored credential is used. Grants stay in memory.
"""
import hashlib,hmac,http.cookiejar,json,math,re,secrets,time
import urllib.parse,urllib.request
from datetime import datetime
from io import BytesIO
from PIL import Image
from .radar import LEVELS,pack_composite
BASE='https://panahon.gov.ph'
from .maps import project,philippines

class Session:
 def __init__(self):
  self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  raw=self.read(BASE+'/?trg=iframe&req=radar.rain-rate',250_000).decode()
  self.meta=dict(re.findall(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"',raw))
  if any(not self.meta.get(key) for key in ('csrf-token','api-sig','embed-grant')):raise ValueError('PAGASA public session unavailable')
 def read(self,url,limit,headers=None):
  req=urllib.request.Request(url,headers={'User-Agent':'Roddy-Weather-Commander/0.4',**(headers or {})})
  with self.opener.open(req,timeout=20) as response:raw=response.read(limit+1)
  if len(raw)>limit:raise ValueError('PAGASA response exceeds limit')
  return raw
 def get(self,path,params,limit):
  ts=str(int(time.time()));nonce=secrets.token_hex(16)
  value='\n'.join(['GET',path.strip('/'),ts,nonce]).encode()
  headers={'Referer':BASE+'/','X-Ts':ts,'X-Nonce':nonce,'X-Embed-Grant':self.meta['embed-grant'],
   'X-Sig':hmac.new(self.meta['api-sig'].encode(),value,hashlib.sha256).hexdigest()}
  return self.read(BASE+path+'?'+urllib.parse.urlencode({'token':self.meta['csrf-token'],**params}),limit,headers)

def mercator(lat):return math.log(math.tan(math.pi/4+math.radians(lat)/2))

def encode_rain(raw,metadata,stamp):
 bounds=metadata['bounds'];scale=metadata['scale']
 if len(bounds)!=4 or not all(isinstance(n,(float,int)) and math.isfinite(n) for n in bounds):raise ValueError('PAGASA bounds')
 west,south,east,north=bounds
 if not (90<west<east<150 and -10<south<north<40):raise ValueError('PAGASA geographic coverage')
 if scale.get('mode')!='rain' or scale.get('unit')!='mm/hr' or scale.get('sqrt') is not True or scale.get('max')!=80:raise ValueError('PAGASA rain encoding changed')
 image=Image.open(BytesIO(raw))
 if not 2<=image.width<=2048 or not 2<=image.height<=2048:raise ValueError('PAGASA raster size')
 image=image.convert('RGBA');source=image.load()
 picture=philippines()
 top=mercator(north);height=top-mercator(south)
 for y in range(224):
  lat=19.5-(y-12)/15.4;sy=int((top-mercator(lat))/height*image.height)
  for x in range(336):
   lon=121.2+(x-142)/15;sx=int((lon-west)/(east-west)*image.width)
   if not (0<=sx<image.width and 0<=sy<image.height):continue
   r,_,_,alpha=source[sx,sy]
   rain=(r/255)**2*80
   if alpha>=90 and rain>=.5:picture.putpixel((x,y),LEVELS[sum(rain>=t for t in (5,6.9,15,30,50,80))])
 return pack_composite(picture,stamp,country=1)

def fetch_philippines():
 session=Session()
 reply=json.loads(session.get('/api/v1/radar/timeline',{'sublayer':'mosaic-rainrate'},200_000))
 metadata=reply['data'];timeline=metadata['timeline']
 if not reply.get('success') or metadata.get('no_data') or not timeline:raise ValueError('PAGASA radar unavailable')
 stamp=max(row['observed_at_unix'] for row in timeline)
 if not isinstance(stamp,(float,int)) or not math.isfinite(stamp):raise ValueError('PAGASA timestamp')
 # Fetch by observation time, not a shifting timeline index.
 raw=session.get('/api/v1/radar-data-image',{'t':stamp,'mode':'rain','size':1024,'v':metadata['tile_version']},4_000_000)
 return encode_rain(raw,metadata,datetime.fromtimestamp(stamp).astimezone())
