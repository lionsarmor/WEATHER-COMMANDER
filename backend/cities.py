"""Bounded city search messages shared by HostFS and the modem HTTP bridge."""
import math, unicodedata, urllib.parse
from .weather import fetch_json

REQUEST_SIZE=64
REPLY_SIZE=256

def ascii_text(value,limit):
 return unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().upper()[:limit]

def validate_request(raw):
 if len(raw)!=64 or raw[:4]!=b'WCC1' or raw[4] not in (1,2,3):raise ValueError('Invalid city request')
 if int.from_bytes(raw[60:62],'little')!=sum(raw[:60]) or raw[55]!=0:raise ValueError('Invalid city checksum')
 query=raw[8:56].split(b'\0',1)[0].decode('ascii')
 if any(ord(c)<32 or ord(c)>126 for c in query):raise ValueError('Invalid city text')
 return query.strip(),int.from_bytes(raw[56:60],'little')

def search(query):
 if not 2<=len(query)<=47:raise ValueError('Enter at least two letters')
 params=urllib.parse.urlencode({'name':query,'count':5,'language':'en','format':'json'})
 data=fetch_json('https://geocoding-api.open-meteo.com/v1/search?'+params)
 matches=[]
 for row in data.get('results',[])[:5]:
  lat=float(row['latitude']);lon=float(row['longitude']);ident=int(row['id'])
  if not math.isfinite(lat) or not -90<=lat<=90 or not math.isfinite(lon) or not -180<=lon<=180:raise ValueError('Invalid coordinates')
  if not 0<ident<2**32:raise ValueError('Invalid location ID')
  name=ascii_text(row['name'],14)
  region=row.get('admin1') or row.get('country_code','')
  label=ascii_text(f"{row['name']}, {region}",27)
  matches.append({'id':ident,'name':name,'label':label,'latitude':lat,'longitude':lon})
 return matches

def reply(request,status,message,matches=()):
 out=bytearray(256);out[:64]=request;out[64]=status;out[65]=len(matches)
 out[66:96]=ascii_text(message,29).encode().ljust(30,b'\0')
 for i,row in enumerate(matches):
  pos=96+i*32
  out[pos:pos+4]=row['id'].to_bytes(4,'little')
  out[pos+4:pos+32]=row['label'].encode()[:27].ljust(28,b'\0')
 return bytes(out)
