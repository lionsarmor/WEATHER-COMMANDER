# Direct Wi-Fi setup

Weather Commander has two modes: offline demo, and a real X16 with a compatible
TexElec Serial & ESP32 / ZiModem Wi-Fi card. A bridge computer is not required.

1. Open Settings, then Wi-Fi and connections.
2. Choose **On a real Commander X16**. Select a scanned network, or choose
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
and clearly labeled recorded radar. The desktop launcher uses this same app;
it does not start a host feed or use your computer's Internet connection.

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
