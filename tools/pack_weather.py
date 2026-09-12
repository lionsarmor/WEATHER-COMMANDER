#!/usr/bin/env python3
"""Pack normalized weather JSON into the bounded X16 snapshot ABI (no network)."""
import argparse, json, os, tempfile
from pathlib import Path
CITY_IDS=['metro','new_york','los_angeles','chicago','houston','miami','denver','seattle','boston','san_francisco']
CONDITIONS={'clear':0,'sunny':1,'cloudy':2,'rain':3}
FIELDS={'temperature_f':(-128,127),'humidity_pct':(0,100),'wind_mph':(0,200),
        'tonight_low_f':(-128,127),'tomorrow_high_f':(-128,127),
        'pressure_hundredths_above_29':(0,200),'visibility_miles':(0,100)}
def pack(document):
 records=document['cities']
 if len(records)!=10 or {r['id'] for r in records}!=set(CITY_IDS):
  raise ValueError('Exactly the ten documented, unique city IDs are required')
 by_id={r['id']:r for r in records}
 out=bytearray(128);out[:6]=b'WC16\x01\x0a'
 for i,cid in enumerate(CITY_IDS):
  r=by_id[cid]
  for field,(lo,hi) in FIELDS.items():
   value=r[field]
   if type(value) is not int or not lo<=value<=hi:raise ValueError(f'{cid}.{field}: expected integer {lo}..{hi}')
  if r['condition'] not in CONDITIONS:raise ValueError(f'{cid}: unknown condition')
  values=[r['temperature_f'],CONDITIONS[r['condition']],r['humidity_pct'],r['wind_mph'],
          r['tonight_low_f'],r['tomorrow_high_f'],r['pressure_hundredths_above_29'],r['visibility_miles']]
  out[16+i*8:24+i*8]=bytes(v&255 for v in values)
 out[8:10]=sum(out[16:96]).to_bytes(2,'little')
 return bytes(out)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
 args=p.parse_args();data=pack(json.loads(args.input.read_text()))
 args.output.parent.mkdir(parents=True,exist_ok=True)
 # Readers see either the old complete snapshot or the new complete snapshot.
 with tempfile.NamedTemporaryFile(dir=args.output.parent,delete=False) as f:
  tmp=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
 try:os.replace(tmp,args.output)
 finally:tmp.unlink(missing_ok=True)
 print(f'Wrote {len(data)} bytes to {args.output}')
if __name__=='__main__':main()
