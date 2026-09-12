%import ui
cities {
    sub draw() {
        ubyte i
        ubyte x
        ubyte y
        ubyte color
        ui.text(2,42,$15,iso:"SELECT A CITY")
        for x in 40 to 58 {
            ui.cell(x,41,188,$45)
            ui.cell(x,43,189,$45)
        }
        ui.fill(40,42,19,1,$45)
        ui.centered(40,42,19,1,$45,iso:"+ ADD CITY [N]")
        for i in 0 to 9 {
            x=2+i/5*29
            y=44+i % 5*2
            color=$16
            if i==state.city color=$51
            ui.fill(x,y,28,2,color)
            ui.centered(x+1,y,14,2,color,state.city_name(i))
            ui.table_temperature(x+15,y,color,state.field(i,0))
            ui.centered(x+20,y,8,2,color,state.condition(state.field(i,1)))
            if i==state.city ui.centered(x,y,1,2,color,iso:">")
        }
    }
    sub reading(ubyte x, ubyte y, ubyte width, word value, ubyte suffix) {
        ubyte size=2
        bool negative=value<0
        if negative value=-value
        if value>=10 size+=2
        if value>=100 size+=2
        if negative size++
        if suffix!=0 size++
        ui.fill(x,y,width,3,$16)
        x+=(width-size)/2
        if negative { ui.cell(x,y+1,45,$15)
            x++ }
        if value>=100 { ui.bigdigit(x,y,((value as uword)/100) as ubyte)
            x+=2 }
        if value>=10 { ui.bigdigit(x,y,((value as uword)/10 % 10) as ubyte)
            x+=2 }
        ui.bigdigit(x,y,((value as uword) % 10) as ubyte)
        if suffix==127 ui.cell(x+2,y,127,$15)
        else if suffix!=0 ui.cell(x+2,y+1,suffix,$15)
    }
    sub temperature(ubyte x, ubyte y, ubyte width, ubyte raw) {
        word value=raw as byte
        if state.units==1 value=(value-32)*5/9
        reading(x,y,width,value,127)
    }
    sub panel() {
        ui.heading(iso:"CITY SPOTLIGHT")
        ui.card(20,12,38,13,state.city_name(state.city))
        ui.icon(23,16,state.field(state.city,1))
        temperature(29,16,10,state.field(state.city,0))
        ui.centered(40,16,17,2,$25,state.condition(state.field(state.city,1)))
        ui.centered(40,19,8,1,$24,iso:"HIGH")
        ui.centered(49,19,8,1,$24,iso:"LOW")
        temperature(40,21,8,state.field(state.city,5))
        temperature(49,21,8,state.field(state.city,4))
        ui.card(20,26,18,8,iso:"HUMIDITY")
        reading(22,28,14,state.field(state.city,2) as word,37)
        ui.bar(22,32,14,state.field(state.city,2))
        ui.card(40,26,18,8,iso:"WIND / MPH")
        reading(42,28,14,state.field(state.city,3) as word,0)
        ui.centered(42,32,14,1,$24,iso:"SURFACE WIND")
        ui.button(20,36,38,2,$45,iso:"OPEN THIS CITY'S LOCAL REPORT >")
        ui.button(20,39,10,2,$45,iso:"< CITY")
        ui.button(31,39,16,2,$51,iso:"FORECAST >")
        ui.button(48,39,10,2,$45,iso:"CITY >")
    }
}
