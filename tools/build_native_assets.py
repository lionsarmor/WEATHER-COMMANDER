#!/usr/bin/env python3
"""Bounded PH radar basemap, loaded after PNG history banks are released."""
import struct
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
    print(f'Native PH basemap: {len(book)} tiles, {len(result)} bytes')
    return result

if __name__ == '__main__':
    build()
