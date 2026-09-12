"""Deterministic upstream response for weather adapter and compiled-client tests."""
from datetime import datetime,timedelta

def weather_fixture():
 result=[]
 start=datetime(2026,9,10)
 for station in range(10):
  hours=[start+timedelta(hours=n) for n in range(168)]
  result.append({'current':{'time':'2026-09-10T14:30','temperature_2m':70+station,'relative_humidity_2m':48,
   'apparent_temperature':72+station,'is_day':1,'weather_code':3,'pressure_msl':1015.2,
   'wind_speed_10m':8,'wind_direction_10m':225,'visibility':16093.44,'dew_point_2m':50},
   'hourly':{'time':[h.isoformat(timespec='minutes') for h in hours],
    'temperature_2m':[50+n%24+station for n in range(168)],'weather_code':[3]*168,
    'precipitation_probability':[n%101 for n in range(168)],'uv_index':[2.5]*168},
   'daily':{'time':[(start+timedelta(days=n)).date().isoformat() for n in range(7)],
    'temperature_2m_max':[80+station+n for n in range(7)],'temperature_2m_min':[50+station+n for n in range(7)],
    'weather_code':[3,61,0,95,71,45,2],'precipitation_probability_max':[10,80,0,90,60,0,20],
    'sunrise':[(start+timedelta(days=n,hours=6,minutes=25)).isoformat(timespec='minutes') for n in range(7)],
    'sunset':[(start+timedelta(days=n,hours=19,minutes=8)).isoformat(timespec='minutes') for n in range(7)]}})
 return result
