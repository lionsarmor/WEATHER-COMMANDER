%import ui
%import map_icons
map {
    ubyte[9] xs=[21,20,24,32,40,36,49,51,49]
    ubyte[9] ys=[14,22,28,21,17,30,22,13,33]
    ubyte[9] stations=[7,9,2,6,3,4,1,8,5]
    sub draw() {
        ubyte i
        if state.page==state.REGIONAL { regional()
            return }
        if state.country==1 { philippines()
            return }
        ui.heading(iso:"UNITED STATES / NATIONAL WEATHER")
        for i in 0 to 8 {
            marker(xs[i],ys[i],stations[i])
        }
        if state.extended ui.text(19,39,$26,iso:"OPEN-METEO / CURRENT MODEL WEATHER")
        else ui.text(19,39,$26,iso:"DEMO WEATHER / CONNECT FOR LIVE DATA")
    }
    sub philippines() {
        ui.heading(iso:"PHILIPPINES / NATIONAL WEATHER")
        station(19,18,1,iso:"MANILA")
        station(19,13,2,iso:"BAGUIO")
        station(49,19,3,iso:"LEGAZPI")
        station(19,28,4,iso:"P.PRINCESA")
        station(19,23,5,iso:"ILOILO")
        station(49,25,6,iso:"CEBU")
        station(49,13,7,iso:"TACLOBAN")
        station(49,33,8,iso:"DAVAO")
        station(19,33,9,iso:"ZAMBOANGA")
        if state.extended ui.centered(19,39,40,2,$26,iso:"OPEN-METEO / CLICK A CITY TO EXPLORE")
        else ui.centered(19,39,40,2,$26,iso:"DEMO WEATHER / CONNECT FOR LIVE DATA")
    }
    sub marker(ubyte x, ubyte y, ubyte city) {
        ubyte i
        ubyte kind=state.field(city,1)
        uword glyph
        if kind>6 kind=6
        ; 24px symbols lead each marker; the temperature uses the smaller font.
        for i in 0 to 8 {
            glyph=map_icons.glyphs[kind*9+i]
            %asm {{ php
                sei }}
            ui.at(x+i%3,y+i/3)
            cx16.VERA_DATA0=lsb(glyph)
            cx16.VERA_DATA0=msb(glyph)
            %asm {{ plp }}
        }
        ui.fill(x+3,y+1,5,2,$15)
        ui.table_temperature(x+3,y+1,$15,state.field(city,0))
    }
    sub station(ubyte x, ubyte y, ubyte city, str label) {
        ui.text(x,y-1,$26,label)
        marker(x,y,city)
    }
    sub regional() {
        ubyte i
        ubyte city
        ubyte y
        ui.heading(iso:"REGIONAL WEATHER WATCH")
        if state.country==0 ui.card(20,12,38,27,iso:"CENTRAL US / CITY COMPARISON")
        else ui.card(20,12,38,27,iso:"LUZON / VISAYAS / MINDANAO")
        for i in 0 to 2 {
            city=3
            if i==1 city=6
            if i==2 city=4
            if state.country==1 {
                city=1
                if i==1 city=6
                if i==2 city=8
            }
            y=15+i*8
            ui.text(22,y,$25,state.city_name(city))
            ui.icon(22,y+2,state.field(city,1))
            ui.bigtemp(29,y+2,state.field(city,0))
            ui.text(37,y+2,$26,state.condition(state.field(city,1)))
            ui.text(37,y+4,$24,iso:"HUMIDITY")
            ui.number(47,y+4,$26,state.field(city,2))
            ui.cell(50,y+4,37,$26)
        }
        if state.extended ui.text(21,40,$24,iso:"OPEN-METEO / THREE REGIONAL STATIONS")
        else ui.text(21,40,$24,iso:"DEMO / CONNECT FOR CURRENT WEATHER")
    }
    sub local() {
        ui.heading(iso:"YOUR LOCAL WEATHER")
        ui.card(20,12,38,13,state.city_name(state.city))
        ui.icon(23,16,state.field(state.city,1))
        ui.bigtemp(30,16,state.field(state.city,0))
        ui.text(39,16,$25,state.condition(state.field(state.city,1)))
        ui.text(39,19,$24,iso:"FEELS LIKE")
        if state.extended ui.temperature(40,21,$25,state.detail(8))
        else ui.text(40,21,$26,iso:"DEMO")
        ui.card(20,26,18,9,iso:"RAIN CHANCE")
        ui.card(40,26,18,9,iso:"SUNRISE / SET")
        if state.extended {
            ui.bigpercent(24,28,state.detail(10))
            ui.bar(22,33,14,state.detail(10))
            ui.time(44,28,$25,state.detail(18),state.detail(19))
            ui.time(44,31,$25,state.detail(20),state.detail(21))
            ui.text(21,37,$24,iso:"AS OF")
            ui.time(28,37,$26,state.detail(22),state.detail(23))
            ui.text(35,37,$24,iso:"CITY LOCAL TIME")
        } else {
            ui.text(26,30,$24,iso:"DEMO")
            ui.text(46,28,$24,iso:"--:--")
            ui.text(46,31,$24,iso:"--:--")
        }
        ui.button(20,39,10,2,$45,iso:"< CITY")
        ui.button(31,39,16,2,$51,iso:"FORECAST >")
        ui.button(48,39,10,2,$45,iso:"CITY >")
    }
}
