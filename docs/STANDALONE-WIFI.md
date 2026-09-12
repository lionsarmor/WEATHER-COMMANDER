# Standalone Wi-Fi recovery checkpoint

**Unpublished and not integrated into the application yet.** The user requires
offline demo OR real X16/Wi-Fi calling public APIs, with no computer bridge.
Do not push or release this rewrite until direct weather AND direct radar work
for both USA and Philippines. Work stays on local branch `standalone-wifi`.
Published v0.1.0 and the normal `buildweather` runtime still use the old design.

Run `.venv/bin/python tools/check_native.py` to compile and test the new banks
without changing `dist`, `VERSION`, or release files. Source files survived the
computer crash; the newly created checkpoint document and runner were empty and
have been restored.

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
  cache; compiled, but complete multi-city network/cache flow not yet tested.
- Bank 24 `direct_inflate`: streaming zlib/DEFLATE, stored/fixed/dynamic blocks,
  checked trees/backreferences/output sizes and Adler-32. History uses 26–29.
- Bank 3 `direct_png`: PNG CRC, five filters, 8-bit L/LA/RGB/RGBA/indexed color,
  transparency, bounded scanlines, rejection of placeholders and partial data.
  Current row at `$7001`, previous row in bank 25. Final completion is required
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

## Remaining work

1. Nonce generation, public-session extraction,
   NOAA/PAGASA metadata parsing, signing and image request orchestration.
2. Geographic scanline sampling and bounded radar tile encoding; reject stale
   or unavailable observations honestly. Test both complete fetch/display paths.
3. Native geocoding, saved personal coordinates, country switching, weather
   cache orchestration, progress/cancellation and responsiveness.
4. Loader/build integration, demo/hardware modes, simplified Wi-Fi wizard,
   removal of bridge/file choices and bridge autostart.
5. Packaging/docs, full regression/emulator tests, memory and machine-time
   checks, then release preparation. Do not publish before these are ready.

Banks 1 (radar API) and 23 (geocoding) remain available for code. Bank 25 holds
previous-row storage and pending radar grid; 26–29 are the 32 KiB history.
Existing code 4–19 and graphics 30–63 remain reserved, targeting stock 512 KiB.
HTTP scratch overlaps the radar payload, so exchanges invalidate radar readiness.

Primary references: [ZiModem](https://github.com/bozimmerman/Zimodem),
[Open-Meteo](https://open-meteo.com/en/docs),
[DEFLATE](https://www.rfc-editor.org/rfc/rfc1951),
[PNG](https://www.w3.org/TR/png-3/),
[SHA](https://www.rfc-editor.org/rfc/rfc6234.html).
