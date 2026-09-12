%import ui
%import diskio
%import interaction
%import network_mailbox
city_input {
    &ubyte[64] request=$6b00
    ubyte[48] query
    ubyte[256] response
    ubyte[40] notice
    ubyte[35] entry
    ubyte count=0
    ubyte selected=0
    ubyte serial=0
    bool pending=false
    bool editing=true
    uword started
    extsub @bank 12 $a00c = network_city() clobbers(A,X,Y)
    sub message(str value) { void strings.copy(value,notice) }
    sub draw() {
        ubyte i
        ubyte n=strings.length(query)
        ubyte offset=0
        ubyte color
        ui.heading(iso:"ADD YOUR CITY")
        ui.text(20,12,$26,iso:"CITY NAME / STATE OR COUNTRY")
        ui.text(20,14,$24,iso:"EXAMPLE: MADISON, WI")
        ui.fill(20,16,38,3,$51)
        if n>33 offset=n-33
        for i in 0 to 33 entry[i]=query[offset+i]
        n-=offset
        if editing and not pending { entry[n]=95
            n++ }
        entry[n]=0
        ui.centered(20,16,38,3,$51,entry)
        ui.button(20,20,23,3,$45,iso:"SEARCH CITY >")
        ui.button(45,20,13,3,$45,iso:"< BACK")
        ui.text(20,24,$25,notice)
        if count>0 {
            for i in 0 to count-1 {
                color=$26
                if i==selected and not editing color=$51
                ui.fill(20,26+i*2,38,2,color)
                ui.centered(20,26+i*2,36,2,color,&response+100+(i as uword)*32)
                ui.centered(56,26+i*2,2,2,color,iso:">")
            }
        }
        ui.text(20,38,$24,iso:"YOUR CITY APPEARS FIRST IN THE LIST.")
        ui.text(20,40,$26,iso:"ADDING ANOTHER REPLACES YOUR CITY.")
    }
    sub search() {
        if pending return
        if strings.length(query)<2 { message(iso:"ENTER AT LEAST TWO LETTERS")
            return }
        state.city_action=1
    }
    sub choose() {
        if not pending and count>0 state.city_action=2
    }
    sub leave() {
        pending=false
        state.city_action=0
        state.page=state.CITIES
    }
    sub key() {
        ubyte ch=network_mailbox.key
        ubyte n=strings.length(query)
        if ch==27 { leave()
            return }
        if pending return
        if ch==13 {
            if not editing and count>0 choose()
            else search()
            return
        }
        if count>0 and (ch==17 or ch==145) {
            editing=false
            if ch==17 and selected+1<count selected++
            if ch==145 and selected>0 selected--
            return
        }
        if ch==9 { editing=not editing
            return }
        if ch==20 or ch==8 {
            if n>0 query[n-1]=0
        } else {
            if ch>=$c1 and ch<=$da ch-=$80
            if ch>=97 and ch<=122 ch-=32
            if ch<32 or ch>126 return
            if n>=47 return
            query[n]=ch
            query[n+1]=0
        }
        count=0
        editing=true
        message(iso:"PRESS ENTER OR CLICK SEARCH CITY")
    }
    sub hit() {
        ; Resident core resolves shared navigation before these local targets.
        if interaction.inside(160,128,464,152) interaction.choose(7,1)
        if interaction.inside(160,160,344,184) and not pending interaction.choose(7,2)
        if interaction.inside(360,160,464,184) interaction.choose(7,3)
        if not pending and count>0 and interaction.inside(160,208,464,208+(count as uword)*16) {
            interaction.choose(7,4+((state.mouse_y-208)/16) as ubyte)
        }
    }
    sub click() {
        hit()
        when state.pointer_target {
            1 -> editing=true
            2 -> search()
            3 -> leave()
            else -> { selected=state.pointer_target-4
                editing=false
                choose() }
        }
    }
    sub accept() -> bool {
        uword i
        ubyte status=@($6440)
        for i in 0 to 63 { if @($6400+i)!=request[i as ubyte] return false }
        if status<1 or status>4 or @($6441)>5 return false
        if status==1 and @($6441)==0 return false
        for i in 66 to 255 {
            if i<96 or (i-96) % 32>=4 {
                if @($6400+i)!=0 and (@($6400+i)<32 or @($6400+i)>126) return false
            }
        }
        if @($645f)!=0 return false
        for i in 0 to 4 { if @($647f+i*32)!=0 return false }
        for i in 0 to 255 response[i as ubyte]=@($6400+i)
        pending=false
        count=0
        editing=true
        message(&response+66)
        if status==1 {
            count=response[65]
            selected=0
            editing=false
        }
        if status==2 {
            state.city=0
            state.source=2
            state.page=state.CITIES
            state.city_action=3
        }
        state.city_dirty=true
        return true
    }
    sub send() {
        ubyte i
        ubyte operation=state.city_action
        uword checksum=0
        state.city_action=0
        serial++
        for i in 0 to 63 request[i]=0
        request[0]=87
        request[1]=67
        request[2]=67
        request[3]=49
        request[4]=operation
        request[5]=serial
        for i in 0 to 47 request[8+i]=query[i]
        if operation==2 {
            for i in 0 to 3 request[56+i]=response[96+selected*32+i]
        }
        for i in 0 to 59 checksum+=request[i]
        request[60]=lsb(checksum)
        request[61]=msb(checksum)
        count=0
        pending=true
        started=cbm.RDTIM16()
        message(iso:"SEARCHING / PLEASE WAIT")
        if operation==2 message(iso:"LOADING YOUR CITY'S WEATHER")
        ui.clear_center()
        draw()
        if network_mailbox.url[0]!=0 {
            network_city()
            if network_mailbox.complete and network_mailbox.received==256 {
                if accept() return
            }
        }
        if diskio.f_open_w(iso:"@:WCQUERY.BIN") {
            if not diskio.f_write(request,64) pending=false
            diskio.f_close_w()
        } else pending=false
        if not pending message(iso:"COULD NOT SAVE / PLEASE RETRY")
    }
    sub tick() {
        uword size
        if not pending return
        if diskio.f_open(iso:"WCCITIES.BIN") {
            size=diskio.f_read($6400,257)
            diskio.f_close()
            if size==256 { if accept() return }
        }
        if cbm.RDTIM16()-started>=2700 {
            pending=false
            editing=true
            state.city_dirty=true
            message(iso:"NO CONNECTION / PLEASE RETRY")
        }
    }
}
