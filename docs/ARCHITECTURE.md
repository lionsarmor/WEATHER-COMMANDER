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
| 4 | WCIDENT.BIN | Time-of-day selection and the scenery tilemap |
| 5 | WCGEOG.BIN | National map, regional comparison, local weather |
| 6 | WCCOND.BIN | Selected city's current/tonight/tomorrow statistics |
| 7 | WCCITY.BIN | City selector and directory |
| 8 | WCFCST.BIN | Seven-day and hourly forecasts |
| 9 | WCRADAR.BIN | National radar display |
| 10 | WCSET.BIN | Clickable settings cards |
| 11 | WCABOUT.BIN | About and help |
| 12 | WCNET.BIN | TexElec/ZiModem driver, scan/join, bounded HTTP transfer |
| 13 | WCPROV.BIN | Demo/file/network provider, validation, freshness |
| 14 | WCWIFI.BIN | Full-page Wi-Fi setup and credential entry |
| 15 | WCRFEED.BIN | Country radar validation, demo fallback, VRAM upload |
| 16 | WCPREF.BIN | Load/save session preferences |
| 17 | WCADD.BIN | City text entry, search results, selection and request polling |
| 18 | WCHOME.BIN | Country picker and bounded country request polling |
| 19 | WCBANNER.BIN | Centered double-size clock/location; reserved bitmap at $AE80–$BFFF |
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
| `$69C0–$6A88` | Setup controls, status, URL and transfer mailbox |
| `$6B00–$6B3F` | Bounded city search/selection request shared with the network bank |
| `$6C00–$6D00` | Bounded modem response transcript |
| `$6D20–$6D5F` | Two bounded strings for the clock/location banner |
| `$7000–$931F` | Country radar tile payload and map; extra read byte at `$9320` |
| `$9800–$9821` | Shared app state |
| `$9840–$988F` | Compact ten-city current-weather records |
| `$9A00–$9BFF` | Saved system palette |
| `$9C00–$9C06` | Saved Layer 1 registers |

All snapshots validate before replacing active weather. The extra weather-read
byte at `$6800` detects oversized files without touching the scan mailbox.
Radar has a separate bounded area. Credential and URL buffers are cleared on
startup; passwords are never copied into the preference file.

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

NOAA's CONUS reflectivity raster is fetched separately from any map or labels.
The bridge selects the newest CONUS raster ID, preserving its observation time
(overseas mosaics may have different times). It reprojects the transparent
echo layer onto the same spherical Albers map as the dashboard. Samples use
two-pixel cells; rare tiles simplify to occupied four-pixel quadrants instead
of borrowing a different storm pattern. A bounded 207-tile codebook includes
seven stable legend swatches. The map remains native resolution underneath.
Palette 15 provides green terrain, mint borders, blue ocean scanlines and brighter
blue/green/yellow/orange/red/magenta
echoes. WCR4 maps explicitly select that palette; the loader rejects WCR2/WCR3 files.
The 8,992-byte feed uses conventional RAM, and cannot overwrite text, weather
icons, the shell, or either text map. Stale radar is hidden even in manual mode.

The Wi-Fi bank owns a five-view wizard (choice, networks, password, weather
computer, ready). Detection is part of scanning; joining advances to the
weather address. A bare host/IP becomes an HTTP URL on port 8767. The computer
path reads the host snapshot without probing the modem. Get Weather and Save
actions are delegated to the resident core to keep bank calls and I/O bounded.
The wizard owns its footer and suspends the dashboard ticker.

The real 60 Hz jiffy clock drives weather refresh (30/60/120 seconds), the clock,
and ticker. Unsigned subtraction handles ordinary 16-bit timer rollover. The
clock checks weather age even when automatic fetching is disabled. File I/O
and modem operations are synchronous but bounded. Exit restores the system
palette, original Layer 1 registers, ROM charset, and cleared BASIC screen.

See [host bridge and Wi-Fi](HOST-BRIDGE.md) and [wire formats](SNAPSHOT.md).

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
Country switching reuses the bounded city wire envelope with operation 3 and
blocks conflicting requests until success, failure or the 45-second timeout.

The banner uses a 280×32 pixel bitmap in bank 19 and 140 reserved layer-0
tiles. The shared 5×7 font is doubled to 10×14 with a 12-pixel advance. Each
line is centered independently and has one pixel of vertical breathing room
inside its 16-pixel line. Unchanged strings skip both rendering and VRAM writes.

Philippine radar uses PAGASA/Panahon's public rain-rate timeline and timestamp-keyed
raster. The public browser-session handshake stays inside the bridge. The first
channel decodes to `(R/255)^2 * 80` mm/h; alpha masks missing data. Web Mercator
source bounds are reprojected to the native island map. Terrain and echoes share
the 207-tile budget; sampling is coarsened in place only when necessary.

Radar demo state is at $9821. Recorded samples load from WCRDEMO/WCRDPH; the flag
is checksummed and cannot pass live validation. Fresh modem data has priority
over SD cache. Wi-Fi displays radar readiness separately from weather.
