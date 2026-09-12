%import ui
%import map_icons
conditions {
    sub icon(ubyte x, ubyte y, ubyte kind) {
        ubyte i
        uword glyph
        if kind>6 kind=6
        for i in 0 to 8 {
            glyph=map_icons.glyphs[kind*9+i]
            %asm {{ php
                sei }}
            ui.at(x+i%3,y+i/3)
            cx16.VERA_DATA0=lsb(glyph)
            cx16.VERA_DATA0=msb(glyph)
            %asm {{ plp }}
        }
    }
    sub label(ubyte y, str title) {
        ui.centered(63,y,9,2,$14,title)
    }
    sub number(ubyte y, ubyte value, bool percent) {
        ubyte[5] text
        ubyte n=0
        if value>=100 { text[n]=value/100+48
            n++ }
        if value>=10 { text[n]=value/10 % 10+48
            n++ }
        text[n]=value % 10+48
        n++
        if percent { text[n]=37
            n++ }
        text[n]=0
        ui.centered(73,y,5,2,$14,text)
    }
    sub draw() {
        uword pressure=2900+state.field(state.city,6)
        ubyte[6] reading
        ; Own the whole column so old text and shell separators cannot bleed
        ; through between the padded rows or the two compact forecast cards.
        ui.fill(62,9,17,32,$16)
        ui.centered(62,9,17,2,$15,state.city_name(state.city))
        ui.centered(62,11,17,1,$16,iso:"CURRENTLY")
        icon(63,13,state.field(state.city,1))
        ui.bigtemp(69,13,state.field(state.city,0))
        ui.centered(62,16,17,2,$16,state.condition(state.field(state.city,1)))
        ui.centered(62,18,10,2,$14,iso:"FEELS LIKE")
        if state.extended ui.table_temperature(73,18,$16,state.detail(8))
        else ui.centered(73,18,5,2,$16,iso:"--")
        label(20,iso:"HUMIDITY")
        number(20,state.field(state.city,2),true)
        label(22,iso:"WIND MPH")
        number(22,state.field(state.city,3),false)
        label(24,iso:"PRESSURE")
        if state.extended pressure=state.detail(16)+(state.detail(17) as uword)*256
        reading[0]=(pressure/1000) as ubyte+48
        reading[1]=(pressure/100 % 10) as ubyte+48
        reading[2]=46
        reading[3]=(pressure/10 % 10) as ubyte+48
        reading[4]=(pressure % 10) as ubyte+48
        reading[5]=0
        ui.centered(73,24,5,2,$14,reading)
        label(26,iso:"DEW POINT")
        if state.extended ui.table_temperature(73,26,$14,state.detail(9))
        else ui.centered(73,26,5,2,$14,iso:"--")
        label(28,iso:"VISIB MI")
        number(28,state.field(state.city,7),false)
        ui.button(62,30,17,2,$24,iso:"TONIGHT LOW")
        if state.extended icon(63,32,state.detail(14))
        else icon(63,32,0)
        ui.bigtemp(69,32,state.field(state.city,4))
        ui.button(62,35,17,2,$24,iso:"TOMORROW HIGH")
        if state.extended icon(63,37,state.detail(15))
        else icon(63,37,1)
        ui.bigtemp(69,37,state.field(state.city,5))
    }
}
