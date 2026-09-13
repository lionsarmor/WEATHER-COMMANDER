# Weather and radar wire formats

These are internal bank-to-bank formats. The native Wi-Fi workers create them
from public JSON/PNG responses; the application no longer reads host-generated
weather/radar files or hexadecimal bridge endpoints. Headers, sizes, checksums,
indices, ranges and timestamps validate before data reaches the display.

## WCW2 weather: 1,024 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | 4 | ASCII `WCW2` |
| 4 | 2 | Version 2, ten stations |
| 6 | 1 | Latest upstream fetch healthy: 0/1 |
| 7 | 1 | Radar has been fetched: 0/1; radar is validated separately |
| 8 | 2 | Little-endian additive checksum of bytes 6–7 and 10–1023 |
| 10 | 5 | Fetch year minus 1900, month, day, hour, minute (X16-local) |
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
7 windy. Unavailable upstream values cause the native provider to retain a stale prior
snapshot; they are not replaced with fabricated zero readings.

Stations: home (Chicago initially), New York, Los Angeles, Chicago, Houston,
Miami, Denver, Seattle, Boston, San Francisco. Settings can make any selected
station the startup home. Native station coordinates are in `src/direct_stations.p8`.
The Add City screen replaces the first station with a saved personal location;
the other nine stations retain their names and coordinates.

Philippine stations: personal Manila initially, Manila, Baguio, Legazpi,
Puerto Princesa, Iloilo, Cebu, Tacloban, Davao, Zamboanga. The country byte
selects the station labels and map together with the validated observations.

## City search and selection

The native Add City screen sends a bounded in-memory request to bank 12.
That bank calls Open-Meteo geocoding directly and returns up to five matches.
Selecting a match resolves its ID, stages coordinates and fetches all ten
forecasts. Failure restores the previous personal station. Save preferences
persists the coordinates; no query/reply files are used.

A request is 64 bytes: `WCC1` at 0–3, operation (1 search, 2 select city) at 4,
request serial at 5, reserved at 6–7, NUL-terminated ASCII query at 8–55,
little-endian location ID at 56–59, additive checksum of 0–59 at 60–61, and
reserved at 62–63. A response is 256 bytes: an exact echo of the request at
0–63, status at 64 (1 matches, 2 added, 3 no match, 4 lookup/weather failure),
count at 65, NUL-terminated notice at 66–95, then five 32-byte results starting
at 96. Each result has a four-byte location ID and a 28-byte NUL-terminated
ASCII label. The client rejects mismatched requests, malformed sizes and text;
network failures retain the editable query for retry. Country changes use a
separate resident transaction and also work with the two offline demo assets.

## WCR4 country radar: 8,992 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | 4 | ASCII `WCR4` |
| 4 | 1 | Tile count, 1–207 |
| 5 | 1 | Country: 0 USA / NOAA, 1 Philippines / PAGASA |
| 6 | 5 | Provider observation timestamp, converted to X16-local time |
| 11 | 1 | Recorded demo flag: 0 actual feed, 1 bundled demo |
| 12 | 2 | Little-endian checksum of bytes 4–11 and 14–8991 |
| 14 | 1 | Last upstream attempt failed: 0 healthy, 1 failed |
| 15 | 1 | Reserved |
| 16 | 6,624 | Up to 207 4bpp tiles, padded with zeroes |
| 6640 | 2,352 | 42×28 map, little-endian tile IDs 257 through 256+tile count, OR `$F000` (palette 15) |

The first tile is transparent; the next seven are stable solid legend swatches.
Remaining US tiles represent precipitation echoes over the native basemap.
Philippine tiles combine the island geography and rain rate in the same tile
budget. The client rejects older WCR2/WCR3 payloads.

Country, demo and health flags are covered by the checksum. Live validation
rejects demo-marked packets. Freshness limits are
15 minutes for US and 30 minutes for PH; midnight/month/year rollover is handled.
WCRDEMO.BIN and WCRDPH.BIN are packaged recorded samples, accepted only through
the demo path and always labeled as such. Native radar downloads are PNG files
named WCRPNG.BIN; the decoder produces WCR4 in RAM after full image validation.
Invalid, stale or wrong-country images are unavailable in Wi-Fi mode.

## WS3 preferences: 100 bytes

`WCSETUP.BIN` contains `WS`, version 3, units at 3, interval at 4,
automatic mode at 5, source (0 demo / 2 card) at 6, home index at 7, and country
at 8. Bytes 9–15 are reserved. Bytes 16–55 and 56–95 contain the US and PH
personal station: NUL-terminated latitude (12 bytes), longitude (12), name (16).
Bytes 96–97 indicate whether each station is set. Bytes 98–99 hold the
little-endian sum of bytes 0–97. The loader checks ranges, string bounds,
coordinates and checksum before changing app state.

The old 144-byte WS2 file can migrate display preferences, ignoring its bridge
URL and mapping the old local-file source to demo. The app only overwrites
preferences after Save. Passwords are not stored. The original WC16 packer
remains a development reference; it is not an application data-source option.
