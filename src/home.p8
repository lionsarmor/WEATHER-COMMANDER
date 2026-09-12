%import ui
%import diskio
%import network_mailbox
home {
    &ubyte[64] request=$6b00
    ubyte serial=128
    uword started
    extsub @bank 12 $a00c = network_country() clobbers(A,X,Y)
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
            ui.centered(19,38,40,2,$26,iso:"CHECK YOUR WEATHER BRIDGE CONNECTION")
        } else {
            ui.centered(19,35,40,2,$25,iso:"CLICK A POSTCARD OR PRESS 1 / 2")
            ui.centered(19,38,40,2,$24,iso:"YOUR PERSONAL CITY IS SAVED PER COUNTRY")
        }
    }
    sub accept() -> bool {
        ubyte i
        for i in 0 to 63 { if @($6400+i)!=request[i] return false }
        if @($6440)!=2 and @($6440)!=4 return false
        if @($6441)!=0 return false
        state.country_status=2
        if @($6440)==2 state.country_status=3
        return true
    }
    sub choose() {
        ubyte i
        uword checksum=0
        if state.country_status==1 return
        if state.country_choice==state.country {
            state.country_status=0
            state.page=state.NATIONAL
            return
        }
        state.country_status=1
        serial++
        for i in 0 to 63 request[i]=0
        request[0]=87
        request[1]=67
        request[2]=67
        request[3]=49
        request[4]=3
        request[5]=serial
        request[8]=85
        request[9]=83
        if state.country_choice==1 {
            request[8]=80
            request[9]=72
        }
        for i in 0 to 59 checksum+=request[i]
        request[60]=lsb(checksum)
        request[61]=msb(checksum)
        started=cbm.RDTIM16()
        draw()
        if network_mailbox.url[0]!=0 {
            network_country()
            if network_mailbox.complete and network_mailbox.received==256 {
                if accept() return
            }
        }
        if diskio.f_open_w(iso:"@:WCQUERY.BIN") {
            if not diskio.f_write(request,64) state.country_status=2
            diskio.f_close_w()
        } else state.country_status=2
    }
    sub tick() {
        uword size
        if state.country_status!=1 return
        if diskio.f_open(iso:"WCCITIES.BIN") {
            size=diskio.f_read($6400,257)
            diskio.f_close()
            if size==256 { if accept() return }
        }
        if cbm.RDTIM16()-started>=2700 state.country_status=2
    }
}
