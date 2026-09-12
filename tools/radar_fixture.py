"""Deterministic test-only radar using recorded pixels with a controlled clock."""
from pathlib import Path
from datetime import datetime
from backend.radar import configure,checksum

def radar_fixture(country=0,stamp=None,demo=False):
 stamp=stamp or datetime.now().astimezone()
 name='demo-ph.bin' if country else 'demo-us.bin'
 raw=bytearray((Path(__file__).resolve().parents[1]/'assets/radar'/name).read_bytes())
 raw[6:11]=bytes([stamp.year-1900,stamp.month,stamp.day,stamp.hour,stamp.minute]);raw[14]=0
 return configure(raw,country,demo)
