"""Open-Meteo adapter. All temperatures are Fahrenheit on the X16 wire."""
from datetime import datetime, timedelta
import json, math, urllib.parse, urllib.request

CITIES=[('CHICAGO HOME',41.85,-87.65),('NEW YORK',40.71,-74.01),
 ('LOS ANGELES',34.05,-118.24),('CHICAGO',41.85,-87.65),('HOUSTON',29.76,-95.37),
 ('MIAMI',25.76,-80.19),('DENVER',39.74,-104.99),('SEATTLE',47.61,-122.33),
 ('BOSTON',42.36,-71.06),('SAN FRANCISCO',37.77,-122.42)]
CURRENT='temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,pressure_msl,wind_speed_10m,wind_direction_10m,visibility,dew_point_2m'
HOURLY='temperature_2m,weather_code,precipitation_probability,uv_index'
DAILY='temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,sunrise,sunset'

def fetch_json(url):
 request=urllib.request.Request(url,headers={'User-Agent':'Roddy-Weather-Commander/0.2 (personal weather display)'})
 with urllib.request.urlopen(request,timeout=15) as response:
  raw=response.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('Weather response exceeds limit')
  return json.loads(raw)

def condition(code,day=True):
 if code==0:return 1 if day else 0
 if code in (1,2,3):return 2
 if code in (45,48):return 6
 if code in (71,73,75,77,85,86):return 4
 if code in (95,96,99):return 5
 if code in (51,53,55,56,57,61,63,65,66,67,80,81,82):return 3
 raise ValueError(f'Unknown WMO code {code}')

def integer(value,lo=0,hi=255):
 if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Missing weather value')
 result=round(value)
 if not lo<=result<=hi:raise ValueError(f'Weather value {result} outside {lo}..{hi}')
 return result&255

def fetch_weather(cities=None):
 cities=CITIES if cities is None else cities
 params={'latitude':','.join(str(c[1]) for c in cities),'longitude':','.join(str(c[2]) for c in cities),
  'current':CURRENT,'hourly':HOURLY,'daily':DAILY,'temperature_unit':'fahrenheit',
  'wind_speed_unit':'mph','timezone':'auto','forecast_days':7}
 data=fetch_json('https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(params))
 if not isinstance(data,list) or len(data)!=10:raise ValueError('Incomplete station response')
 return data

def snapshot(data, fetched_at=None, healthy=True, radar=False, cities=None, country=0):
 """WCW2: 32-byte header, 10x32 observations, 10x28 daily, 10x24 hourly, headline."""
 cities=CITIES if cities is None else cities
 if len(data)!=10 or len(cities)!=10:raise ValueError('Expected ten cities')
 fetched_at=fetched_at or datetime.now().astimezone()
 out=bytearray(1024);out[:6]=b'WCW2\x02\x0a';out[6]=int(healthy);out[7]=int(radar)
 out[10:15]=bytes([fetched_at.year-1900,fetched_at.month,fetched_at.day,fetched_at.hour,fetched_at.minute])
 if country not in (0,1):raise ValueError('Unknown country')
 out[15]=country
 for i,city in enumerate(data):
  c=city['current'];d=city['daily'];h=city['hourly'];now=datetime.fromisoformat(c['time'])
  at=next(n for n,t in enumerate(h['time']) if datetime.fromisoformat(t)>=now.replace(minute=0,second=0))
  start=now.replace(hour=18,minute=0,second=0)
  if now.hour<8:start-=timedelta(days=1)
  finish=start+timedelta(hours=14)
  night=[n for n,t in enumerate(h['time']) if max(start,now)<=datetime.fromisoformat(t)<=finish]
  if not night:raise ValueError('No overnight forecast')
  lo=min(h['temperature_2m'][n] for n in night)
  night_code=max(h['weather_code'][n] for n in night)
  pressure=round(c['pressure_msl']*0.0295299830714*100)
  if not 2000<=pressure<=3500:raise ValueError('Invalid sea-level pressure')
  sunrise=datetime.fromisoformat(d['sunrise'][0]);sunset=datetime.fromisoformat(d['sunset'][0])
  row=[integer(c['temperature_2m'],-128,127),condition(c['weather_code'],c['is_day']),
   integer(c['relative_humidity_2m'],0,100),integer(c['wind_speed_10m'],0,200),
   integer(lo,-128,127),integer(d['temperature_2m_max'][1],-128,127),max(0,min(200,pressure-2900)),
   integer(c['visibility']/1609.344,0,100),integer(c['apparent_temperature'],-128,127),
   integer(c['dew_point_2m'],-128,127),integer(max(h['precipitation_probability'][at:at+12]),0,100),
   integer(h['uv_index'][at]*10,0,250),round(c['wind_direction_10m']/22.5)%16,
   int(c['is_day']),condition(night_code,False),condition(d['weather_code'][1]),
   pressure&255,pressure>>8,sunrise.hour,sunrise.minute,sunset.hour,sunset.minute,
   now.hour,now.minute,0,0,1,now.weekday(),now.day,0,0,0]
  out[32+i*32:64+i*32]=bytes(row)
  for n in range(7):
   p=352+i*28+n*4
   out[p:p+4]=bytes([integer(d['temperature_2m_max'][n],-128,127),integer(d['temperature_2m_min'][n],-128,127),
    condition(d['weather_code'][n]),integer(d['precipitation_probability_max'][n],0,100)])
  for n in range(8):
   p=632+i*24+n*3;j=at+n
   out[p:p+3]=bytes([integer(h['temperature_2m'][j],-128,127),condition(h['weather_code'][j]),integer(h['precipitation_probability'][j],0,100)])
 hottest=max(range(10),key=lambda i:data[i]['current']['temperature_2m'])
 headline=f"OPEN-METEO MODEL WEATHER / {cities[hottest][0]} {round(data[hottest]['current']['temperature_2m'])}F / SELECT A CITY FOR HOURLY AND 7-DAY FORECASTS / NOAA RADAR"
 out[872:1000]=(headline.encode('ascii')[:124]+b' / ').ljust(128,b'\0')
 # Home display name, so the adapter can replace the fictional station.
 out[1000:1016]=cities[0][0].encode('ascii')[:14].ljust(16,b'\0')
 out[8:10]=((sum(out[6:8])+sum(out[10:]))&65535).to_bytes(2,'little')
 return bytes(out)
