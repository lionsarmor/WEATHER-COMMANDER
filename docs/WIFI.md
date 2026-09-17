# Direct Wi-Fi setup

Weather Commander has two modes: offline demo, and direct internet through a
compatible TexElec Serial & ESP32 / ZiModem Wi-Fi card. This can be a physical
card or the card emulated by X16-emulator-wifi-support. A bridge computer is
not required.

1. Open Settings, then Wi-Fi and connections.
2. Choose **Connect with a Wi-Fi card**. Select a scanned network, or choose
   **Hidden network? Enter its name**.
3. Enter the network name and password. Tab switches fields; uppercase matters.
   Leave the password empty for an open network. Click **Connect to Wi-Fi**.
4. Once connected, click **Get my weather**. The card requests public APIs itself.
5. Click **Save and open weather** to preserve your preferences.

If no modem is found, check that the card uses its default IO7-low address
`$9FE0`. The native driver uses 115200 baud, 8N1 and hardware flow control.
The supported stock ZiModem command set includes ATW network joining and ATDS
raw TLS connections. No replacement firmware is installed by this app.
An already configured card can fetch weather immediately on startup.

Use **Explore the offline demo** when a card or network is unavailable. This
provides sample weather, hourly and seven-day forecasts, both country maps,
and clearly labeled recorded radar. The normal desktop launcher uses this same
app with the stock emulator and starts in demo mode without a card.

## Wi-Fi emulator

Run `WEATHERWIFI`, or `./run.sh --wifi` from the project. This uses the custom
`Desktop/X16-emulator-wifi-support/x16-emulator/build/x16emu` with `-wifi`.
Select **X16-EMULATOR-NET**, leave the password empty, then connect and get weather.
The emulator uses the computer's internet connection while the X16 app performs
its own HTTP, weather parsing, and radar decoding. No weather bridge is started.
`WEATHER_WIFI_EMULATOR` can override the executable path; put `rom.bin` beside it.

The custom emulator needs raw `ATDS` TLS support, not just its `AT&G` HTTPS
helper. Rebuild it with OpenSSL development files installed. Older builds
ignored the secure dial modifier, so joining appeared successful while weather
requests failed. Socket closes must also preserve Wi-Fi association, and receive
buffer backpressure is required for full forecasts and radar.

`python3 tools/smoke_wifi_live.py` tests the actual app, ROM, UART, TLS, scan/join,
and ten-city live public API downloads using an isolated test directory. Live
NOAA radar was also downloaded and decoded successfully in this test.

If aliases still point to the old Desktop folder, update them for
`Desktop/Roddy Software/WEATHER COMMANDER` and reload with `source ~/.bash_aliases`.

## Data and saved preferences

Weather is cached for 15 minutes. Radar is downloaded to `WCRPNG.BIN` on the
SD card, so the app directory must be writable for live radar. Philippine
radar takes about five minutes to decode in the background at X16 speed.
You can switch views while it builds. Stale or invalid images are not shown
as live; press R to retry or check another country if a provider is delayed.

City search uses the selected country. After choosing your personal city,
use **Settings → Save my preferences** to save it. `WCSETUP.BIN` stores both
countries' personal coordinates and display settings. Passwords are cleared
after joining or leaving setup and are not written to that preference file.
Existing version-2 preferences migrate their display settings; their bridge
address is ignored. The saved file is only replaced when you choose Save.

Native protocol, decoder and r49 emulator checks have been performed. Physical
Wi-Fi card end-to-end operation still needs a hardware test.
