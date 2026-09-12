%import ui
forecast {
    sub weekday(ubyte day) -> str {
        when day {
            0 -> return iso:"MON"
            1 -> return iso:"TUE"
            2 -> return iso:"WED"
            3 -> return iso:"THU"
            4 -> return iso:"FRI"
            5 -> return iso:"SAT"
        }
        return iso:"SUN"
    }
    sub draw() {
        ubyte i
        ubyte y
        ui.heading(iso:"YOUR WEATHER AHEAD")
        ui.centered(19,12,40,1,$25,state.city_name(state.city))
        if not state.extended {
            ui.card(20,15,38,20,iso:"DEMO FORECAST")
            ui.icon(23,18,state.field(state.city,1))
            ui.bigtemp(30,19,state.field(state.city,0))
            ui.text(22,25,$24,iso:"TONIGHT LOW")
            ui.temperature(46,25,$25,state.field(state.city,4))
            ui.text(22,29,$24,iso:"TOMORROW HIGH")
            ui.temperature(46,29,$25,state.field(state.city,5))
            ui.button(20,37,38,3,$45,iso:"CONNECT WI-FI FOR HOURLY / 7 DAYS >")
            return
        }
        tabs()
        if state.forecast_mode==1 { hourly()
            return }
        ui.fill(20,16,38,2,$45)
        ui.centered(21,16,6,2,$45,iso:"DAY")
        ui.centered(28,16,5,2,$45,iso:"HIGH")
        ui.centered(34,16,5,2,$45,iso:"LOW")
        ui.centered(40,16,8,2,$45,iso:"SKY")
        ui.centered(50,16,7,2,$45,iso:"RAIN")
        for i in 0 to 6 {
            y=18+i*3
            ui.fill(20,y,38,2,$16)
            if i==0 ui.centered(21,y,6,2,$15,iso:"TODAY")
            else ui.centered(21,y,6,2,$14,weekday((state.detail(27)+i) % 7))
            ui.table_temperature(28,y,$15,state.daily(i,0))
            ui.table_temperature(34,y,$16,state.daily(i,1))
            ui.centered(40,y,8,2,$16,state.condition(state.daily(i,2)))
            percent(50,y,7,state.daily(i,3))
            ; The rain bar owns the third row, below the padded labels.
            ui.bar(28,y+2,29,state.daily(i,3))
        }
        ui.text(20,40,$24,iso:"OPEN-METEO / BARS SHOW RAIN CHANCE")
    }
    sub tabs() {
        ubyte day_color=$45
        ubyte hour_color=$45
        if state.forecast_mode==0 day_color=$51
        else hour_color=$51
        ui.button(20,14,18,2,day_color,iso:"7-DAY OUTLOOK")
        ui.button(39,14,19,2,hour_color,iso:"NEXT 8 HOURS")
    }
    sub hourly() {
        ubyte i
        ubyte x
        ubyte height
        ubyte hour
        ubyte[3] label
        word temperature
        ui.card(19,17,40,16,iso:"TEMPERATURE TREND")
        for i in 0 to 7 {
            ; Eight five-cell columns fit completely inside the forty-cell chart.
            x=19+i*5
            temperature=state.hourly(i,0) as byte
            temperature=(temperature+40)/12
            if temperature<1 temperature=1
            if temperature>10 temperature=10
            height=temperature as ubyte
            ui.fill(x+1,32-height,3,height,$45)
            ui.table_temperature(x,30-height,$15,state.hourly(i,0))
            hour=(state.detail(22)+i) % 24
            label[0]=hour/10+48
            label[1]=hour % 10+48
            label[2]=0
            ui.centered(x,33,5,2,$24,label)
            percent(x,37,5,state.hourly(i,2))
        }
        ui.centered(19,36,40,1,$24,iso:"RAIN CHANCE (%)")
        ui.centered(19,40,40,1,$24,iso:"CITY LOCAL TIME (24H) / OPEN-METEO")
    }
    sub percent(ubyte x, ubyte y, ubyte width, ubyte value) {
        ubyte[5] label
        ubyte n=0
        if value>=100 { label[n]=49
            n++ }
        if value>=10 { label[n]=value/10 % 10+48
            n++ }
        label[n]=value % 10+48
        label[n+1]=37
        label[n+2]=0
        ui.centered(x,y,width,2,$14,label)
    }
}
