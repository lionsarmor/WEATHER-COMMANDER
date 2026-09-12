Weather Commander brings a cable-weather dashboard to the Commander X16: USA and Philippines maps, current conditions, hourly and seven-day forecasts, city search, NOAA/PAGASA radar, guided Wi-Fi setup, and 28 rotating pixel landscapes.

Download **WEATHER-COMMANDER-X16.zip**, extract it, and copy the entire **WEATHER** folder to your SD card. All 58 required PRG/BIN files are included. At the X16 BASIC prompt:

```basic
DOS "CD:WEATHER"
LOAD "WEATHER.PRG",8
RUN
```

Use ROM r49 and at least 512 KB RAM. Without a live connection, the application starts in its clearly labeled demo.

For live data, also download **WEATHER-COMMANDER-BRIDGE.zip** and run its Python bridge on your computer. Its `START-HERE.txt` covers Linux/macOS and Windows. In the app, open **Settings → Wi-Fi and connections** and follow the setup. Real X16 networking requires a compatible TexElec Serial & ESP32 / ZiModem card.

The build enforces bank limits and passes compiled 65C02 tests, weather/city adapter tests, and archive checks. Local r49 emulator checks exercised 82 mouse routes and all 28 landscapes. Physical Wi-Fi card operation still needs a hardware test. This release also fixes delayed weather fetching immediately after the host computer reboots.

`SHA256SUMS.txt` verifies both downloads. User preferences, saved locations, live snapshots, and passwords are excluded.
