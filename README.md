# WEATHER COMMANDER

A native Prog8 weather station for the Commander X16: a cable-weather dashboard,
USA and Philippines maps, current conditions, hourly and seven-day forecasts,
city search, NOAA/PAGASA radar, and 28 rotating pixel landscapes.

**Version 0.2.0 connects directly through the X16 Wi-Fi card.** It replaces
the older bridge design with two modes:
**offline demo** or **a real X16 with a compatible Wi-Fi card calling public APIs
directly**. No bridge computer, API key, or custom modem firmware is required.

![Weather Commander in the X16 emulator](docs/preview.png)

## Download, build and launch

Get [the latest release](https://github.com/lionsarmor/WEATHER-COMMANDER/releases/latest).
Version 0.2.0 ships a single X16 archive; the older v0.1.0 bridge is not needed.

On this development computer:

```sh
WEATHERBUILD          # or buildweather: build ZIP and update the mounted X16 SD card
WEATHERBUILD --no-sd  # build ZIP only
WEATHERCMD            # build changed files and launch the emulator
```

From a checkout, use `./buildweather` and `./run.sh`. The ZIP is
`dist/WEATHER-COMMANDER-X16.zip`, with one ready-to-copy **WEATHER** folder.
All 69 PRG/BIN files, setup instructions, and data notices are included.
`dist/SHA256SUMS.txt` verifies the download. Personal preferences, passwords,
and downloaded radar images are excluded.

After a successful build, the helper looks for a mounted FAT32 card labeled
**X16_SDCARD** and updates its **WEATHER** folder at the card root (on this
computer, `/media/legion/X16_SDCARD/WEATHER`). It preserves saved preferences,
downloaded data, and unrelated files, and verifies the copied files. With no
card mounted, it keeps the ZIP and reports that copying was skipped. Use
`--no-sd` to build without copying; CI always skips the SD step.

Alternatively, copy the complete WEATHER folder from the ZIP to your SD card.
Eject the card before unplugging it. On the X16 (device 8), run:

```basic
DOS "CD:WEATHER"
LOAD "WEATHER.PRG",8
RUN
```

Use ROM r49 and at least 512 KB banked RAM. The emulator starts in demo mode
when no compatible modem is present; the launcher does not start a bridge.

## Connect your X16

Open **Settings → Wi-Fi and connections → On a real Commander X16**.
Choose your network, enter its password, click **Connect to Wi-Fi**, then
**Get my weather**. **Save and open weather** saves your preferences.
The first ten-city update can take a minute. An already configured card can
connect on startup. Without a card or usable initial connection, demo mode
provides complete sample forecasts and recorded radar for both countries.

The driver supports the TexElec Serial & ESP32 card with compatible stock
ZiModem firmware, using IO7 at `$9FE0`, 115200 baud, and hardware flow control.
See [Wi-Fi setup](docs/WIFI.md). Protocol checks and r49 emulator tests pass;
a physical-card end-to-end test has not been performed.

Click **+ ADD CITY [N]**, enter a name such as `Madison, WI`, and choose a result.
Search is restricted to the selected country. Your city becomes the first
station, alongside nine standard cities. Each country keeps its own personal
coordinates. **Save my preferences** preserves both cities on the SD card.
Failed lookups or weather downloads keep the previous city and data.
City search requires Wi-Fi mode; country switching also works in the demo.

## Controls

| Input | Action |
|---|---|
| Mouse | Select navigation, map stations, city rows, forecast tabs and settings |
| Up / Down, Tab | Select a sidebar section |
| Left / Right | Select a city |
| Enter | Open the selected city's local weather |
| F1 / F2 / F3 / F4 / F5 | Help / Cities / Forecast / Radar / Settings |
| F in Forecast | Switch seven-day / hourly chart |
| Click scenery / G | Next landscape |
| R / H / Esc | Refresh / Home / Exit; Esc goes back inside setup |
| Settings: W / U / T / A / D | Wi-Fi / units / interval / automatic / demo or card |
| Settings: C / S | Use selected city as home / save preferences |
| Wi-Fi: 1 / 2 on welcome | Offline demo / real X16 Wi-Fi card |
| Wi-Fi: Tab / Enter / Esc | Select field / continue / back |

The pointer is a white arrow with a black outline and a cloud/sun badge. Its
tip is the click position. The lower-right picture rotates through city,
country, mountains, beach, desert, lighthouse and neon-highway scenes. Each
has dawn, day, dusk and night variants selected by the X16's local clock.
These decorative time bands are separate from the city's actual sunrise/sunset.

## Direct data and radar

[Open-Meteo](https://open-meteo.com/en/docs) supplies current **model** weather
and forecasts. The app checks every minute by default; each country's weather
cache lasts 15 minutes. City reports show the provider's local observation time.

[NOAA/NWS](https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer)
supplies the US reflectivity image. The request locks a specific observation
and uses the dashboard's exact map projection.
[PAGASA/Panahon](https://panahon.gov.ph/?trg=iframe&req=radar.rain-rate)
supplies the Philippine rain-rate mosaic. The X16 obtains its public session,
signs the requests, downloads the PNG to SD, and decodes it in banked RAM.
Both countries use geographically aligned, bounded radar tiles.

Radar checks run on roughly five-minute US and ten-minute Philippine schedules.
US decoding takes seconds; the full Philippine image takes about five minutes
at 8 MHz in r49 emulation. A progress bar appears while the map builds, and you
can keep using other screens. A previous fresh map remains available until its
replacement validates. PNG checksums, image size, coordinates, scale and
observation time are checked before a new map becomes live. US observations
older than 15 minutes and Philippine observations older than 30 minutes are
hidden. A provider outage or stale timeline produces an unavailable message.

Offline radar is always **RADAR DEMO / NOT LIVE**. Its recorded samples are
packaged separately from live downloads; see [sample provenance](assets/radar/NOTICE.md).
A failed weather refresh retains previous data with a **STALE** label.
Passwords are masked and cleared after use; the preference file stores display
settings and personal coordinates, not Wi-Fi credentials.

## Toolchain and verification

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
./tools/setup-toolchain.sh
./buildweather --check
python3 tools/smoke_emulator.py
python3 tools/smoke_mouse.py
```

The setup script downloads checksum-verified Prog8 12.3.2 and 64tass 1.60.3243.
Install Java 21 or newer, curl, unzip, make and a C compiler first. For emulator
launch, place r49 `x16emu` and `rom.bin` in `.tools/x16emu/`. `X16_TOOLS` selects
an alternate toolchain root. This workspace can reuse DESK COMMANDER's installed
toolchain without modifying that project.

Compiled 65C02 tests cover native HTTP/UART/SD transfer, JSON/weather, caching,
geocoding, SHA/HMAC, UTC timestamps, streaming DEFLATE/PNG, map sampling,
preferences, country transitions and UI controls. Real r49 tests verify boot,
exit, menu pixels, 75 mouse routes, all landscapes, and complete PNG-to-radar
processing. For a downloaded test image, run:

```sh
python3 tools/smoke_native_app.py us /path/to/noaa-84x56.png
python3 tools/smoke_native_app.py ph /path/to/pagasa-750x1024.png
```

`backend/` contains development reference code and asset-building helpers; Python
is not shipped to or needed by the X16. The app's code and data use banks 1–63,
with bank 0 reserved for the ROM. See [architecture](docs/ARCHITECTURE.md) and
[recovery checkpoint](docs/STANDALONE-WIFI.md). Build sizes are recorded in
`build/banks.json` and `build/assets.json`.

[Project](https://github.com/lionsarmor/WEATHER-COMMANDER) ·
[Published releases](https://github.com/lionsarmor/WEATHER-COMMANDER/releases)
