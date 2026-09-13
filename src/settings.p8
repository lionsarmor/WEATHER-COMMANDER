%import ui
settings {
    sub row(ubyte y, str key, str title, str value) {
        ui.fill(19,y,40,3,$45)
        ui.centered(20,y,3,3,$45,key)
        ui.centered(24,y,19,3,$45,title)
        ui.centered(44,y,14,3,$45,value)
    }
    sub draw() {
        ui.heading(iso:"MAKE IT YOUR WEATHER")
        ui.fill(19,13,40,5,$26)
        ui.button(19,13,40,3,$45,iso:"W  WI-FI AND CONNECTIONS  >")
        if state.status==3 ui.centered(19,16,40,2,$26,iso:"ONLINE / AUTOMATIC WEATHER UPDATES")
        else ui.centered(19,16,40,2,$26,iso:"CONNECT FOR WEATHER / DEMO OFFLINE")
        if state.units==0 row(19,iso:"U",iso:"TEMPERATURE",iso:"FAHRENHEIT")
        else row(19,iso:"U",iso:"TEMPERATURE",iso:"CELSIUS")
        when state.interval {
            30 -> row(23,iso:"T",iso:"CHECK EVERY",iso:"30 SECONDS")
            60 -> row(23,iso:"T",iso:"CHECK EVERY",iso:"60 SECONDS")
            else -> row(23,iso:"T",iso:"CHECK EVERY",iso:"120 SECONDS")
        }
        if state.automatic row(27,iso:"A",iso:"AUTOMATIC REFRESH",iso:"ON")
        else row(27,iso:"A",iso:"AUTOMATIC REFRESH",iso:"OFF")
        when state.source {
            0 -> row(31,iso:"D",iso:"WEATHER SOURCE",iso:"DEMO")
            2 -> row(31,iso:"D",iso:"WEATHER SOURCE",iso:"WI-FI CARD")
        }
        ui.fill(19,35,40,2,$26)
        ui.centered(20,35,7,2,$24,iso:"C HOME")
        ui.centered(28,35,30,2,$25,state.city_name(state.home))
        if state.saved ui.button(19,38,40,3,$51,iso:"PREFERENCES SAVED")
        else ui.button(19,38,40,3,$51,iso:"S  SAVE MY PREFERENCES")
    }
}
