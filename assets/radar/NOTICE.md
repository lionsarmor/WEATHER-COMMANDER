# Recorded offline radar samples

These are recorded examples, not current conditions or simulated forecasts.
They are always packaged with the WCR4 demo flag and shown as DEMO / NOT LIVE.
Connecting replaces the sample only after a fresh radar payload is validated.

- `demo-us.bin`: NOAA/NWS CONUS base reflectivity, observed 2026-09-11 21:32 America/Chicago (2026-09-12 02:32 UTC).
  Source: https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer
- `demo-ph.bin`: PAGASA/Panahon mosaic rain rate, observed 2026-09-12 10:20 Asia/Manila (2026-09-12 02:20 UTC).
  Source: https://www.pagasa.dost.gov.ph/radar and its public embedded map https://panahon.gov.ph/?trg=iframe&req=radar.rain-rate
  The public map's timeline supplies the observation time, bounds and numeric rain encoding.

Both samples are reduced to the native X16 display and palette. They are not
endorsed by their data providers. Philippine geography is Natural Earth public
domain data; see assets/data/NOTICE.md. An empty echo area can mean no detected
rain or missing radar coverage; it does not guarantee clear weather.
