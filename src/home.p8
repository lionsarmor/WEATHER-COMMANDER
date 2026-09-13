%import ui
%import network_mailbox
home {
    sub draw() {
        ubyte us=$45
        ubyte ph=$45
        ui.heading(iso:"PICK YOUR CORNER OF THE WORLD")
        ui.centered(19,12,40,2,$26,iso:"WHERE SHALL WE CHECK THE SKIES?")
        if state.country==0 us=$51
        else ph=$51
        ui.button(20,14,18,2,us,iso:"UNITED STATES")
        ui.button(40,14,18,2,ph,iso:"PHILIPPINES")
        ui.centered(20,26,18,1,$26,iso:"CITY LIGHTS")
        ui.centered(40,26,18,1,$26,iso:"ISLAND DAYS")
        ui.centered(20,28,18,1,$24,iso:"COAST TO COAST")
        ui.centered(40,28,18,1,$24,iso:"LUZON TO MINDANAO")
        ui.button(20,30,18,3,us,iso:"1 / EXPLORE >")
        ui.button(40,30,18,3,ph,iso:"2 / TARA NA! >")
        if state.country_status==1 ui.button(20,35,38,3,$45,iso:"PACKING YOUR FORECAST...")
        else if state.country_status==2 {
            ui.centered(19,35,40,2,$25,iso:"COULD NOT LOAD / PICK AGAIN TO RETRY")
            ui.centered(19,38,40,2,$26,iso:"CHECK WI-FI / OR CHOOSE DEMO")
        } else {
            ui.centered(19,35,40,2,$25,iso:"CLICK A POSTCARD OR PRESS 1 / 2")
            ui.centered(19,38,40,2,$24,iso:"YOUR PERSONAL CITY IS SAVED PER COUNTRY")
        }
    }
    sub choose() {
        if state.country_choice==state.country {
            state.country_status=0
            state.page=state.NATIONAL
        } else state.country_status=3
    }
    sub tick() { }
}
