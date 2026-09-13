# WEATHER COMMANDER architecture

The resident program owns the shell, navigation, branding, bottom banners,
clock, input, scheduler, and transitions. Every content application is a
separately compiled Prog8 library with a jump table at `$A000`. Calls return
to the resident shell; a module never switches out the bank containing its own
executing code. The compiler checks code plus BSS against each bank ceiling,
and the build checks every packaged bank against 8,192 bytes.

| Bank | Binary | Responsibility |
|---|---|---|
| Resident | WEATHER.PRG | Shell, input, clock, ticker, scheduler |
| 1 | WCRAPI.BIN | NOAA/PAGASA metadata, public session, signed image requests |
| 2 | WCHASH.BIN | SHA/HMAC and UTC timestamps |
| 3 | WCPNG.BIN | Streaming PNG reader, CRC and scanline filters |
| 4 | WCIDENT.BIN | Time-of-day selection and the scenery tilemap |
| 5 | WCGEOG.BIN | National map, regional comparison, local weather |
| 6 | WCCOND.BIN | Selected city's current/tonight/tomorrow statistics |
| 7 | WCCITY.BIN | City selector and directory |
| 8 | WCFCST.BIN | Seven-day and hourly forecasts |
| 9 | WCRADAR.BIN | National radar display |
| 10 | WCSET.BIN | Clickable settings cards |
| 11 | WCABOUT.BIN | About and help |
| 12 | WCNET.BIN | TexElec/ZiModem scan/join and native geocoding |
| 13 | WCPROV.BIN | Demo/native weather validation and freshness |
| 14 | WCWIFI.BIN | Full-page Wi-Fi setup and credential entry |
| 15 | WCRFEED.BIN | Radar scheduling, map cache, validation and VRAM upload |
| 16 | WCPREF.BIN | Load/save session preferences |
| 17 | WCADD.BIN | City text entry, search results, selection and native request handoff |
| 18 | WCHOME.BIN | Country picker and transactional profile changes |
| 19 | WCBANNER.BIN | Centered double-size clock/location; reserved bitmap at $AE80–$BFFF |
| 20 | WCHTTP.BIN | Stock ZiModem raw TLS, HTTP framing, RAM/SD downloads |
| 21 | WCJSON.BIN | JSON parsing and one-city weather decoding |
| 22 | WCWEATH.BIN | Ten-city requests and two 15-minute country caches |
| 23 | WCRMAKE.BIN | Cooperative radar sampling and bounded tile packing |
| 24 | WCZLIB.BIN | Streaming zlib/DEFLATE with Adler validation |
| 25 | Working RAM | Previous PNG row and pending 84×56 radar grid |
| 26–29 | Working RAM | 32 KiB DEFLATE history; bank 26 reused for PH basemap after decode |
| 30–31 | WCHART / WCPH | Country postcard and Philippines maps for layer 1 |
| 32–35 | WCNAT / WCREG / WCRAD / WCBLK | Cached artwork maps |
| 36–63 | WCSC00.BIN–WCSC27.BIN | Seven landscapes × dawn/day/dusk/night; 6,080 bytes each |

Normal library code/BSS ends below `$C000`. The station library ends below
`$A800`; its scene pixels live in independent data banks. Builds include
exact binary sizes in `build/banks.json` and VRAM allocations in
`build/assets.json`. Use at least 512 KB banked RAM.

## Conventional RAM

| Address | Use |
|---|---|
| Below `$6000` | Resident code; compiler-enforced ceiling |
| `$6000–$63FF` | Active 1,024-byte weather snapshot |
| `$6400–$6800` | Bounded weather staging (extra byte detects oversized files) |
| `$6801–$694F` | Ten scanned SSIDs and scan selection |
| `$6950–$6970` | Selected/typed SSID |
| `$6980–$69BF` | Password; masked and cleared after use/exit |
| `$69C0–$6A88` | Setup controls and transfer mailbox; former URL space unused |
| `$6B00–$6B3F` | Bounded city search/selection request shared with the network bank |
| `$6C00–$6D00` | Bounded modem response transcript |
| `$6D20–$6D5F` | Two bounded strings for the clock/location banner |
| `$6D70–$6EFF` | Native HTTP / JSON / weather mailboxes |
| `$6F00–$6FFF` | PNG / inflate / radar / crypto / UTC mailboxes |
| `$7000–$931F` | HTTP body, PNG row, then completed radar payload; shared scratch |
| `$8000–$8FFF` | HTTP request, fully sent before body overwrites it |
| `$9800–$9821` | Shared app state |
| `$9840–$988F` | Compact ten-city current-weather records |
| `$9890–$98E1` | Two personal coordinate/name records and validity flags |
| `$9A00–$9BFF` | Saved system palette |
| `$9C00–$9C06` | Saved Layer 1 registers |

All snapshots validate before replacing active weather. The extra weather-read
byte at `$6800` detects oversized files without touching the scan mailbox.
Native exchanges reuse the radar scratch. Bank 15 keeps the validated radar
header and tilemap in private BSS, while its tiles remain in VRAM. Restoring
that cache preserves the displayed map across weather requests. PNG compressed
input stays in bank 3 and previous-row/history data stay in banks 25–29, so
HTTP requests between completed scanlines cannot corrupt the decoder.
Passwords are cleared after use and never copied into the preference file.

## VERA

| VRAM | Use |
|---|---|
| `$00000–$04E7F` | Up to 628 static shell/map tiles (see build/assets.json for count) |
| `$04E80–$05FFF` | 140 dynamic header tiles (628–767); 280×32 pixels |
| `$06000–$077BF` | 190 scenery tiles, streamed from one 6,080-byte data bank |
| `$08000–$0BFFF` | Layer 0 artwork tilemap |
| `$0C000–$0FFFF` | Layer 1 text map A |
| `$10000–$1201F` | Text, large digits, basic weather icons, transparent tile |
| `$12020–$139FF` | 207 streamed radar tiles (glyphs 257–463) |
| `$13A00–$13FFF` | Snow, storm, fog icons (glyphs 464–511) |
| `$14000–$157FF` | Paired glyphs 512–703 for vertically centered labels |
| `$15800–$17FFF` | Country artwork glyphs 704–1023 (bounded atlas) |
| `$1B000–$1EFFF` | Layer 1 text map B |
| `$18000–$183FF` | Two custom 32×32 4bpp pointer frames |
| `$1FA00` | Artwork/text palettes; badge slot 10, scenery slots 11–14, radar slot 15 |
| `$1FC00` | Sprite 0 attributes; ROM positioning, custom pixels, palette 0 |

Both layers use 4bpp 8×8 tiles at 640×480. Normal redraws paint the inactive
text map and flip it. Wi-Fi covers the dashboard body while retaining the top
and bottom banners. The station owns only x480–631/y344–423, changes at local
05:00/08:00/17:00/20:00, and cycles themes every 30 seconds or on click/G.
These are visual time bands, not computed sunrise/sunset. The resident core
streams the requested bank into the fixed scenery tile window; no module
switches away its own executable code. Unchanged scenes cause no VRAM writes.

Navigation uses half-cell edge glyphs 188/189 for a 16-pixel highlight centered
on its seven-pixel label. Card headers, buttons, tabs and selected list rows use
the shared centered-label renderer. Paired glyphs 512–703 preserve every text
pixel while adding four pixels above and five below in a two-row bar. Three-row
controls use the middle row, and labels are horizontally centered within their
control or table column. Text map B is at `$1B000`, clear of the expanded font.
One hit map drives mouse dispatch and hover state; Wi-Fi exports its own banked
hit map. The ROM maintains sprite zero with a (0,0) click tip. Both cursor
frames contain the same plain white arrow with a black outline. Its source-pixel tip is (0,7);
the ROM sprite offset is (0,-7), keeping the visible arrow tip at the click coordinate.

NOAA's CONUS request locks the newest valid raster and requests an 84×56 PNG
in the dashboard's spherical Albers projection. Native integer color decoding
maps it to seven reflectivity levels. PAGASA uses the public embedded page's
session values and HMAC-SHA-256 signature; UTC comes from HTTP Date rather
than assuming the X16 clock's timezone. Its 750×1024 gray/alpha PNG is sampled
through verified bounds and rain-rate scale into the same 84×56 grid.

Bank 23 processes one scanline per event-loop call. The app continues handling
mouse, keyboard, clock and scenery between calls. Only a complete image with
valid CRC/Adler, dimensions, map coordinates and observation time can reach the
packer. The 207-tile codebook keeps precipitation in its original cells;
if necessary, it simplifies spatial detail in place at 2, 4 or 8 pixels.
Philippine geography and rain share the bounded codebook. `WCPBASE.BIN` is read
only after decoding closes the PNG, reusing released history bank 26.

Bank 15 schedules radar roughly every five minutes (US) or ten minutes (PH),
keeps a previous fresh map while decoding, and rejects stale observations.
The real r49 full-app tests took 7 seconds for US and 299 seconds for PH.
Both matched the geographic pixel reference while UI changes and simulated
weather exchanges repeatedly overwrote the conventional scratch area.

The Wi-Fi wizard has choice, networks, password, connected and ready views.
The choices are demo and real-card mode. Get Weather and Save actions return
to the resident core; no bridge address is stored or requested. City search
and ID resolution run in bank 12 and weather in bank 22. Coordinates are only
committed after all ten new forecasts validate; failure restores the prior
personal station. Preferences use a checksummed 100-byte WS3 file containing
both countries' coordinates. Legacy WS2 display settings migrate on load.

The 60 Hz jiffy clock drives display checks (30/60/120 seconds), clock and
ticker. Bank 22 caches each complete country for 15 minutes. First network
requests are synchronous and bounded; PNG processing is cooperative. Country
changes cancel decoding before switching its working data. Exit closes the
PNG and restores the system palette, Layer 1 registers, ROM charset and BASIC.

See [Wi-Fi setup](WIFI.md) and [internal wire formats](SNAPSHOT.md).

National uses seven full-color 24×24 weather symbols with smaller temperature
labels. Shared tiles occupy control glyphs 0–31 and free space after the country
atlas; the build generates their lookup in `src/map_icons.p8`. They render with
palette zero; ordinary text starts at glyph 32 and transparent fill remains
glyph 256. Palette-zero index 14 supplies green
terrain scanlines; the footer retains its separate neutral-gray palette.
Philippine National and Radar geometry comes from `backend/maps.py`, including
the radar-unavailable map fallback.

Home and National are separate views. Home uses two pixel postcards, and
National chooses the US or Natural Earth Philippines geography according to
the validated snapshot profile. The resident core copies country art from data
banks to the inactive text map; the content bank draws the labels above it.
Country switching commits geography and weather together after a complete
country snapshot loads; offline mode uses its matching complete demo asset.

The banner uses a 280×32 pixel bitmap in bank 19 and 140 reserved layer-0
tiles. The shared 5×7 font is doubled to 10×14 with a 12-pixel advance. Each
line is centered independently and has one pixel of vertical breathing room
inside its 16-pixel line. Unchanged strings skip both rendering and VRAM writes.

Radar demo state is at `$9821`. Recorded samples load from WCRDEMO/WCRDPH
only in demo mode. Their flag is checksummed and cannot pass live validation.
In Wi-Fi mode, a missing or stale observation is shown as unavailable.
