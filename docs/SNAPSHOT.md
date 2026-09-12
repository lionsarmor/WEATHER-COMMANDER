# Weather and radar wire formats

The backend writes `WCDATA.BIN` and `WCRLIVE.BIN` atomically. The native client
validates headers, sizes, checksums, indices, ranges, and timestamps before use.
The network endpoints deliver the same bytes as uppercase hexadecimal prefixed
with `WC2:` and followed by CR/LF. No pointers or credentials occur in a feed.

## WCW2 weather: 1,024 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | 4 | ASCII `WCW2` |
| 4 | 2 | Version 2, ten stations |
| 6 | 1 | Latest upstream fetch healthy: 0/1 |
| 7 | 1 | Radar has been fetched: 0/1; radar is validated separately |
| 8 | 2 | Little-endian additive checksum of bytes 6–7 and 10–1023 |
| 10 | 5 | Fetch year minus 1900, month, day, hour, minute (bridge-local) |
| 15 | 1 | Country profile: 0 USA, 1 Philippines |
| 16 | 16 | Reserved |
| 32 | 320 | Ten 32-byte current/overnight/next-day records |
| 352 | 280 | Ten sets of seven daily records, four bytes each |
| 632 | 240 | Ten sets of eight hourly records, three bytes each |
| 872 | 128 | ASCII headline, NUL terminated |
| 1000 | 16 | Home station name, NUL terminated |
| 1016 | 8 | Reserved |

Current record offsets: 0 signed °F; 1 condition; 2 humidity %; 3 wind mph;
4 overnight low °F; 5 tomorrow high °F; 6 legacy pressure offset above 29.00;
7 visibility miles; 8 feels-like °F; 9 dew point °F; 10 maximum next-12-hour
precipitation chance %; 11 UV index ×10; 12 wind compass index (0–15);
13 daylight flag; 14 overnight condition; 15 tomorrow condition;
16–17 pressure in hundredths of inHg; 18–19 sunrise hour/minute;
20–21 sunset hour/minute; 22–23 observation/model hour/minute (city local);
24–25 reserved; 26 valid flag (1); 27 weekday (Monday=0); 28 local day of month;
29–31 reserved. Temperatures are signed two's-complement bytes.

Daily records: high °F, low °F, condition, precipitation chance %.
Hourly records: temperature °F, condition, precipitation chance %.
Conditions: 0 clear/night, 1 sunny, 2 cloudy, 3 rain, 4 snow, 5 storms, 6 fog,
7 windy. Unavailable upstream values cause the adapter to retain a stale prior
snapshot; they are not replaced with fabricated zero readings.

Stations: home (Chicago initially), New York, Los Angeles, Chicago, Houston,
Miami, Denver, Seattle, Boston, San Francisco. Settings can make any selected
station the startup home. The adapters define coordinates in `backend/weather.py`.
The Add City screen replaces the first station with a saved personal location;
the other nine stations retain their names and coordinates.

Philippine stations: personal Manila initially, Manila, Baguio, Legazpi,
Puerto Princesa, Iloilo, Cebu, Tacloban, Davao, Zamboanga. The country byte
selects the station labels and map together with the validated observations.

## City search and selection

The native Add City screen uses the same bounded messages through HostFS and
`/x16/city.hex?request=<128 hex digits>`. HostFS writes `WCQUERY.BIN`; the bridge
polls it and atomically writes `WCCITIES.BIN`. The bridge searches
[Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api) and returns
up to five matches for explicit selection. A successful selection fetches and
validates the full weather snapshot before saving `locations.json` and responding.

A request is 64 bytes: `WCC1` at 0–3, operation (1 search, 2 select city, 3 select country) at 4,
request serial at 5, reserved at 6–7, NUL-terminated ASCII query at 8–55,
little-endian location ID at 56–59, additive checksum of 0–59 at 60–61, and
reserved at 62–63. A response is 256 bytes: an exact echo of the request at
0–63, status at 64 (1 matches, 2 added, 3 no match, 4 lookup/weather failure),
count at 65, NUL-terminated notice at 66–95, then five 32-byte results starting
at 96. Each result has a four-byte location ID and a 28-byte NUL-terminated
ASCII label. The client rejects mismatched requests, malformed sizes and text;
it times out after 45 seconds and retains the editable query for retry.
These runtime request, response and city preference files are not packaged.

## WCR4 country radar: 8,992 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | 4 | ASCII `WCR4` |
| 4 | 1 | Tile count, 1–207 |
| 5 | 1 | Country: 0 USA / NOAA, 1 Philippines / PAGASA |
| 6 | 5 | Provider observation timestamp, converted to bridge-local time |
| 11 | 1 | Recorded demo flag: 0 actual feed, 1 bundled demo |
| 12 | 2 | Little-endian checksum of bytes 4–11 and 14–8991 |
| 14 | 1 | Last upstream attempt failed: 0 healthy, 1 failed |
| 15 | 1 | Reserved |
| 16 | 6,624 | Up to 207 4bpp tiles, padded with zeroes |
| 6640 | 2,352 | 42×28 map, little-endian tile IDs 257 through 256+tile count, OR `$F000` (palette 15) |

The first tile is transparent; the next seven are stable solid legend swatches.
Remaining US tiles represent precipitation echoes over the native basemap.
Philippine tiles combine the island geography and rain rate in the same tile
budget. The client rejects WCR2/WCR3; update the bridge and client together.

Country, demo and health flags are covered by the checksum. Live validation
rejects demo-marked packets even if copied to WCRLIVE.BIN. Freshness limits are
15 minutes for US and 30 minutes for PH; midnight/month/year rollover is handled.
WCRDEMO.BIN and WCRDPH.BIN are packaged recorded samples, accepted only through
the demo path and always labeled as such. A network transfer is tried before
an SD cache, and invalid, stale or wrong-country packets fall back to the demo.

## Legacy WC16 snapshots

`tools/pack_weather.py` remains available for the original 128-byte version-1
format and demo JSON. It has ASCII `WC16`, version 1, ten stations, an additive
checksum at bytes 8–9 over records 16–95, and ten eight-byte current-weather
records. Those records use the first eight offsets above and conditions 0–3.
Legacy files are labeled FILE SNAPSHOT and have no extended forecast fields.
They are not treated as a live connection.

```sh
python3 tools/pack_weather.py assets/demo-weather.json dist/sdcard/WCDATA.BIN
```

`WCSETUP.BIN` is separate: 144 bytes with `WS`, version 2, units, interval,
automatic mode, source, home index, then a NUL-terminated bridge URL at offset
16. It contains no Wi-Fi password. Distribution packages exclude all three
runtime files and include the bridge source instead.

Country selection uses operation 3 with `US` or `PH` in the query field.
Status 2 means the new country snapshot is ready; failure retains the prior
profile. `locations.json` stores the active country and a personal location per
country, with automatic migration from older `city.json` files. The native
client validates the requested country before displaying the new snapshot.
Philippines snapshots advertise only fresh Philippine radar availability.
