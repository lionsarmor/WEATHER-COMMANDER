%import ui
about {
    sub draw() {
        ui.heading(iso:"THE RODDY WEATHER STATION")
        ui.card(20,12,38,10,iso:"A LITTLE CHANNEL / A BIG WORLD")
        ui.icon(23,15,1)
        ui.text(30,15,$25,iso:"WEATHER COMMANDER")
        ui.text(30,18,$26,iso:"BUILT FOR YOUR X16")
        ui.card(20,24,38,12,iso:"CONNECTED TO THE FORECAST")
        ui.text(22,26,$24,iso:"WEATHER   OPEN-METEO MODEL DATA")
        ui.text(22,29,$24,iso:"RADAR     NOAA / NATIONAL WEATHER")
        ui.text(22,30,$24,iso:"          SERVICE COMPOSITE")
        ui.text(22,33,$26,iso:"DEMO WEATHER WHEN YOU ARE OFFLINE")
        ui.text(21,38,$25,iso:"YOUR WEATHER. DAY AND NIGHT.")
        ui.button(20,39,38,2,$51,iso:"F1 / OPEN THE QUICK START >")
    }
    sub help() {
        ui.heading(iso:"GET TO KNOW YOUR STATION")
        ui.card(20,12,38,12,iso:"EXPLORE THE WEATHER")
        ui.text(22,14,$26,iso:"UP / DOWN    CHOOSE A SECTION")
        ui.text(22,17,$26,iso:"LEFT / RIGHT CHOOSE A CITY")
        ui.text(22,20,$26,iso:"ENTER        LOCAL WEATHER")
        ui.card(20,26,38,12,iso:"MAKE IT YOURS")
        ui.text(22,28,$26,iso:"F3  7-DAY / F SWITCHES TO HOURLY")
        ui.text(22,31,$26,iso:"F5  SETTINGS / W OPENS WI-FI")
        ui.text(22,34,$26,iso:"R   REFRESH / ESC EXIT OR BACK")
        ui.text(21,40,$24,iso:"CLICK TO EXPLORE / G CHANGES SCENERY")
    }
}
