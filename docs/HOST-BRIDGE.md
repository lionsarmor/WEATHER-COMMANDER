# Weather bridge and Wi-Fi

`WEATHERCMD` starts a local bridge, builds the app, and launches the emulator.
The emulator uses the computer's Internet connection through HostFS. The bridge
stops when the emulator closes. No API key is required.

On an X16 with a TexElec Serial & ESP32 card, Weather Commander uses the same
ZiModem initialization, 115200-baud UART at `$9FE0`, network scan, and join
protocol as DESK COMMANDER. The network worker and setup screen have separate
banks. DESK COMMANDER's files and running backend are unchanged.

## Connecting a physical X16

Run the included bridge on a computer reachable from your X16's Wi-Fi network:

```sh
python3 -m pip install -r requirements.txt
python3 -m backend.server --bind 0.0.0.0 --port 8767 --output dist/sdcard
```

Download and extract **WEATHER-COMMANDER-BRIDGE.zip** on your computer. Its
`WEATHER-BRIDGE/START-HERE.txt` includes virtual-environment commands for Linux,
macOS and Windows. The separate **WEATHER-COMMANDER-X16.zip** goes on the X16.
If using the extracted bridge ZIP, use `--output .` instead. Keep this
process running while using the physical X16.

For the easiest start from this project, run `./bridge.sh`. It prints the
weather computer address to enter on the X16 and stays running in that terminal.

1. Open **Settings → Wi-Fi and connections**.
2. Choose **On a real Commander X16**. The app detects the modem and scans.
3. Select your network, enter its password, and click **Connect to Wi-Fi**.
   Use **Hidden network?** to type a network name manually.
4. Enter the address printed by `bridge.sh`, such as `192.168.1.20`. The app
   adds `http://` and port `8767`; full HTTP addresses and custom ports work too.
5. Click **Get my weather**, then **Save and open weather**. This selects live
   updates and saves preferences in the same flow.

In the emulator, choose **On this computer**. This checks the host weather file
without probing the modem or asking for a Wi-Fi password. If no fresh data is
available, the screen explains how to restart/check the computer connection.

Tab changes fields; Enter continues; Esc returns one step; the Close button
returns to Settings. Passwords retain letter case, remain masked, and clear
after joining, backing out, or closing. They are never saved on the SD card.
Preferences store the weather address and display choices. This version does
not save a ZiModem flash profile; rejoin after a cold modem reset if needed.

Detect and scan time out when hardware is absent. Firmware operations run with
bounded waits, so a slow association or radar transfer can briefly pause the
interface. Physical card operation still needs testing; compiled UART protocol
simulation and the real X16 emulator are covered by automated checks.

## Weather and freshness

**+ ADD CITY [N]**, beside the city list, searches by city name and optional
state/country. Choose a matching location to load it into the first list slot.
The other nine stations remain available. The bridge saves this personal city
in `locations.json`, separately for each country; entering another city replaces
that country's personal slot. Older `city.json` files are migrated automatically. Search uses
HostFS in the emulator and the configured weather computer address on hardware.
Restart the app/bridge after updating so the city request worker is running.

[Open-Meteo](https://open-meteo.com/en/docs) supplies current model weather,
hourly forecasts, seven-day forecasts, overnight lows, next-day highs,
humidity, wind, pressure, visibility, feels-like temperature, dew point,
rain chances, and sunrise/sunset. Current values are weather model output,
not an assertion that every city has a real-time instrument observation.

The bridge batches the ten stations and caches weather for ten minutes. The
X16 checks for updates every 60 seconds by default. Current model values
normally update at 15-minute resolution; polling more often does not create
new observations. Individual city screens show the provider's city-local time.

[NOAA/NWS](https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer)
supplies the precipitation-only CONUS base-reflectivity layer. The bridge
selects the latest CONUS raster, retains its actual observation time, and
projects the echoes onto the native map. Echo colors are simplified to fit the
X16 tile budget; the native state borders and separate legend remain crisp.
[PAGASA/Panahon](https://www.pagasa.dost.gov.ph/radar) supplies Philippine mosaic
rain rate. Its public map session supplies the geographic bounds, numeric scale
and observation timestamp; no account or API key configuration is needed.
The bridge caches radar for five minutes and can populate a cold HTTP feed on
demand. US images older than 15 minutes, or Philippine images older than 30
minutes, are replaced by a clearly labeled recorded demo, including when
automatic refresh is disabled. A failed upstream request marks the cache
unavailable for live display. Fresh data automatically replaces the demo.
Update bridge and client together for the WCR4 country/demo/health flags.

After Get My Weather, the connection screen separately reports **RADAR: LIVE
FEED** or **DEMO UNTIL A FRESH FEED ARRIVES**. Joining Wi-Fi alone cannot prove
that an upstream radar observation is current. Samples stay visibly labeled
until a valid current feed arrives. Keep the bridge running for automatic updates.

With no usable data, AUTO starts in the clearly labeled demo. After real data
has been received, a failure preserves it with a **STALE / LAST DATA** label.
Weather older than 20 minutes is marked stale, including in manual-refresh
mode. Clock aging assumes the bridge computer and X16 use the same local time
zone. Nothing replaces a failed feed with invented live readings.

## Standalone and integration

```sh
# Fetch once, without running a server:
python3 -m backend.server --once --output dist/sdcard

# Skip starting the bridge when launching the emulator:
WEATHER_BRIDGE=0 ./run.sh

# Make the launcher's bridge reachable on the LAN:
./bridge.sh
```

`backend/weather.py` and `backend/radar.py` are independent adapters; the server
is a small standard-library HTTP wrapper. They can be imported by the existing
DESK backend if a shared deployment is preferred later. This milestone does not
modify or deploy that service.

The HTTP endpoints are `/health`, `/x16/weather.hex`, and `/x16/radar.hex`.
The two X16 endpoints use `WC2:` followed by bounded uppercase hexadecimal and
CR/LF. ZiModem fetches them with `AT&G`; validation finishes before weather data
is committed. All successful HostFS updates use atomic file replacement.
