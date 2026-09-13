Weather Commander brings a cable-weather dashboard to the Commander X16:
USA and Philippines maps, current conditions, hourly and seven-day forecasts,
city search, NOAA/PAGASA radar, guided Wi-Fi setup, and 28 pixel landscapes.

**Version 0.2.0 — direct Wi-Fi, with complete offline demo mode.**

This version has two modes: offline demo, or a real X16 Wi-Fi card calling
public APIs directly. The computer bridge and its setup address are removed.
The X16 now handles HTTP, PNG/DEFLATE decoding, the public PAGASA session and
request signing, geographic radar sampling, and per-country weather caching.

Download **WEATHER-COMMANDER-X16.zip**, extract it, and copy the entire
**WEATHER** folder to your SD card. All 69 required PRG/BIN files are included.

```basic
DOS "CD:WEATHER"
LOAD "WEATHER.PRG",8
RUN
```

Use ROM r49, at least 512 KB RAM, and a compatible TexElec Serial & ESP32 /
ZiModem card at IO7 for live data. Open Settings → Wi-Fi and connections,
choose your network, enter its password, then Get my weather. No API key,
bridge computer or custom card firmware is required. Save preferences after
choosing a personal city to retain its coordinates.

Philippine radar takes about five minutes to decode at 8 MHz in r49 emulation;
the dashboard remains usable during decoding. Provider outages and stale or
invalid images are reported without presenting them as live. Offline mode
includes complete sample forecasts and recorded radar for both countries.

Validation includes real public API weather for all 20 stations and current
NOAA/PAGASA image downloads, compiled native component and app tests, 75 emulator mouse
routes, menu pixels, all landscapes, and complete native radar decoding inside
the running dashboard. Physical-card end-to-end operation has not been tested.

`SHA256SUMS.txt` verifies the single X16 download. Personal preferences,
coordinates, downloaded images and passwords are excluded from the archive.
