#!/usr/bin/env python3
"""Bounded PH radar basemap, loaded after PNG history banks are released."""
import struct
import copy
from datetime import datetime
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.maps import philippines

def build():
    picture = philippines()
    book, lookup, tilemap = [], {}, bytearray()
    for y in range(0,224,8):
        for x in range(0,336,8):
            raw = bytes(picture.crop((x,y,x+8,y+8)).getdata())
            if raw not in lookup:
                lookup[raw] = len(book)
                book.append(bytes(raw[i]*16+raw[i+1] for i in range(0,64,2)))
            tilemap.extend(struct.pack('<H',lookup[raw]))
    header = bytearray(16)
    header[:8] = b'WCPB'+bytes([len(book),42,28,1])
    result = header+tilemap+b''.join(book)
    result[12:14] = (sum(result[4:12])+sum(result[14:])).to_bytes(4,'little')[:2]
    assert len(book) <= 182 and len(result) <= 8192
    folder = ROOT/'build/native-assets'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'WCPBASE.BIN').write_bytes(result)
    from backend.weather import snapshot, CITIES
    from weather_fixture import weather_fixture
    from backend.countries import PHILIPPINES as ph_cities
    for country, names, filename in ((0,CITIES,'WCDMUS.BIN'),(1,ph_cities,'WCDMPH.BIN')):
        data = copy.deepcopy(weather_fixture())
        if country:
            for city in data:
                for field in ('temperature_2m','apparent_temperature','dew_point_2m'):
                    city['current'][field] += 10
                for section,fields in (('hourly',('temperature_2m',)),('daily',('temperature_2m_max','temperature_2m_min'))):
                    for field in fields: city[section][field] = [n+10 for n in city[section][field]]
        raw=bytearray(snapshot(data,fetched_at=datetime(2026,9,12,14,0),cities=names,country=country))
        raw[872:1000]=b'OFFLINE DEMO / SAMPLE WEATHER / EXPLORE HOURLY + SEVEN DAY FORECASTS / CONNECT YOUR WI-FI CARD FOR PUBLIC API DATA'.ljust(128,b'\0')
        raw[8:10]=((sum(raw[6:8])+sum(raw[10:])) & 65535).to_bytes(2,'little')
        (folder/filename).write_bytes(raw)
    print(f'Native PH basemap: {len(book)} tiles, {len(result)} bytes')
    return result

if __name__ == '__main__':
    build()
