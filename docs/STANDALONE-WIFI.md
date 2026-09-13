# Standalone Wi-Fi recovery checkpoint

The standalone rewrite is integrated into the application. Its release gate
was direct weather AND radar for both USA and Philippines, without a computer
bridge. Native public requests now obtain all 20 cities' weather and fresh
NOAA/PAGASA PNGs; both image paths also pass the full-app r49 decoder test.
The earlier published v0.1.0 uses the old design. Version 0.2.0 replaces it.

Recovery commits `3c560b8` and `7d54f4b` saved the native components before UI
integration. This document records the implementation and tests so a crash
does not lose the task context. `buildweather --check` builds and checks the
complete standalone package. No user branding files were modified.

## Implemented components

- Bank 20 `direct_http`: stock ZiModem `ATDS` raw TLS, bounded HTTP framing,
  chunked responses, SD image download, partial HTML capture, HTTP Date capture,
  UART RTS pause for SD writes. Requests use `$8000..$8fff` and are transmitted
  fully before responses overwrite this shared scratch. Binary downloads need
  Content-Length or chunked framing. SD cache filename is `WCRPNG.BIN`.
- Bank 21 `direct_weather_decode`: shared JSON exports, current conditions,
  hourly and seven-day forecasts, checked units and hourly alignment, signed
  temperatures, large visibility values. JSON exports follow decode in the
  jump table: validate `$a006`, find `$a009`, next `$a00c`, skip `$a00f`.
- Bank 22 `direct_weather`: country weather request builder and 15-minute
  cache; native country/cache transaction tests and live 20-city API checks pass.
- Bank 24 `direct_inflate`: streaming zlib/DEFLATE, stored/fixed/dynamic blocks,
  checked trees/backreferences/output sizes and Adler-32. History uses 26–29.
- Bank 3 `direct_png`: PNG CRC, five filters, 8-bit L/LA/RGB/RGBA/indexed color,
  transparency, bounded scanlines, rejection of placeholders and partial data.
  Current row at `$7001`, previous row in bank 25. Compressed input is buffered
  inside bank 3, so HTTP exchanges between completed rows cannot overwrite it. Final completion is required
  before committing pixels. `ready` alone is not proof of a valid whole image.
- Bank 2 `direct_crypto`: SHA-256 and HMAC-SHA-256, tested against hashlib/hmac,
  including 91-byte public PAGASA grants. `direct_time` converts HTTP Date to
  UTC Unix seconds and parses/formats unsigned 32-bit timestamps. Calendar,
  overflow and word-boundary tests pass independently of the X16 RTC timezone.

Prog8 12.3.2 required workarounds for combined mixed-width subtraction in
Paeth filtering and byte `|=` into word arrays. Tests cover these cases.

The real r49 ROM test decoded a downloaded 750x1024 PAGASA gray/alpha PNG into
1,536,000 bytes matching Pillow exactly. NOAA's 168x80 RGBA image also matched.
Run `.venv/bin/python tools/smoke_direct_png.py path/to/radar.png` with a local
image. It uses an isolated temporary folder. Warp timing is not hardware speed.

## Verified API details

Stock ZiModem 4.0.2 supports `ATDS"host:443"`; raw HTTP avoids its 256-byte AT
command limit and `AT&G` chunked-response restriction. Open-Meteo HTTP/1.0
returns usable close-delimited JSON; image requests should use HTTP/1.1.

PAGASA's public embedded page provides `csrf-token`, `api-sig`, `embed-grant`
near the beginning. Both timeline and image requests were verified WITHOUT
cookies. Sign `GET\n<path without leading slash>\n<Unix seconds>\n<32 hex nonce>`
with HMAC-SHA-256 using the public `api-sig` string. Send X-Ts, X-Nonce,
X-Embed-Grant, X-Sig and Referer. No account/stored secret is involved. Get UTC
from HTTP Date instead of assuming the X16 RTC timezone.

Only `size=1024` produced usable PAGASA images in testing (750x1024, PNG type 4).
Smaller sizes returned 1x1 transparent placeholders. Verified bounds:
`[115.41549141305251,3.801613036809332,129.51730887177652,22.45850950564088]`.
Y is Mercator; rain is `(gray/255)^2*80` mm/hr, with alpha. Validate bounds and
scale before using a precomputed map. Gray level thresholds for .5,5,6.9,15,30,
50,80 mm/hr are 21,64,75,111,157,202,255; alpha must be at least 90.

NOAA ImageServer accepts the exact spherical Albers projection from
`backend/geometry.py` as custom WKT in bboxSR/imageSR. A locked 84x56 png32
export succeeded, eliminating the need for a large reprojection table. Its URL
was 1,651 bytes, hence the 4 KiB request limit. Full map bounds must include
canvas margins. Ignored `build/direct-us-albers-params.json` contains the probe
parameters; it is not a shipped asset or a persistent observation ID.

## Native radar checkpoint after crash recovery

- Bank 1 now obtains and validates NOAA/PAGASA metadata, extracts the public
  PAGASA session, generates nonces, signs requests, and downloads the selected
  image. Native request tests pass, including stale/future rejection. A live
  native request downloaded fresh NOAA and PAGASA frames. An earlier stale
  PAGASA timeline was correctly rejected before its provider updated.
- Bank 23 decodes one PNG row per call and samples an 84x56 geographic grid in
  bank 25. Packing preserves precipitation locations, simplifying within the
  same cells only when needed to stay within 207 tiles. Philippine tiles include
  the checked `WCPBASE.BIN` geography asset, reusing released history bank 26.
- Real r49 ROM PNG-to-WCR4 tests match every reference pixel: USA 67 tiles / 6
  emulated seconds; Philippines 184 tiles / 283 emulated seconds. Both used full
  resolution without simplification. Philippine decoding now uses incremental UI
  scheduling; this timing is not a physical-card test.
- Native wire strings must use `\r\x0a`: Prog8 encodes `\n` as CR even in ISO
  strings. The request builders now emit actual CRLF and signatures actual LF.
- `smoke_direct_radar.py us|ph path.png` runs isolated ROM integration checks.

## Integration and verification

- Bank 12 contains native geocoding alongside scan/join. Queries are URL-escaped
  and country-filtered; selection resolves the exact unsigned ID. Coordinates
  roll back on forecast failure. All tests execute the compiled instructions.
- Complete US/PH offline forecasts ship in WCDMUS/WCDMPH. Source modes are only
  demo and Wi-Fi card. Home changes weather/geography together. The guided
  wizard has no address field and run.sh no longer starts a bridge.
- Bank 15 caches the validated map/header in BSS while tiles remain in VRAM.
  HTTP scratch reuse cannot destroy the displayed map. Radar schedules are
  five minutes US / ten minutes PH; current limits remain 15/30 minutes.
- WS3 preferences store display choices and both countries' personal stations,
  with checksum and coordinate validation. WS2 display preferences migrate
  without using the bridge URL. Passwords remain outside the saved file.
- Full-app r49 tests decode actual downloaded US/PH images with exact geographic
  pixels while switching views and repeatedly overwriting HTTP scratch. Latest
  processing times were 7 seconds US and about 301 seconds PH at emulated 8 MHz.
- The r49 UI smoke verifies 17 frames and menu glyphs; the mouse probe verifies
  75 routes, pointer pixels/hotspot, both countries and all 28 landscapes.
- `test_direct_weather_flow.py --live` obtained and decoded all 20 cities.
  `test_direct_radar.py --live` obtained fresh images for both countries.
  These use native builders/decoders with a Python public-HTTP transport;
  separate UART tests run the native framing/download transport. Physical-card
  end-to-end testing has not been performed and is not claimed.
- `smoke_native_app.py us|ph image.png` tests actual PNG processing, map/cache,
  controls and ROM I/O in the full app with an isolated downloaded-image handoff.
- Version 0.2.0 packages 69 PRG/BIN files in one WEATHER folder plus notices;
  no bridge ZIP, user settings or downloaded image is included.

Banks 1–24 are code, 25–29 native image working data, 30–63 graphics. Bank 0 is
reserved for the ROM. All modules fit their 8 KiB code+BSS ceilings; resident
code stays below $6000. Geo no longer needs a swappable phase bank.

Primary references: [ZiModem](https://github.com/bozimmerman/Zimodem),
[Open-Meteo](https://open-meteo.com/en/docs),
[DEFLATE](https://www.rfc-editor.org/rfc/rfc1951),
[PNG](https://www.w3.org/TR/png-3/),
[SHA](https://www.rfc-editor.org/rfc/rfc6234.html).
