%import ui
%import network_mailbox
%import interaction
wifi {
    ubyte[64] line
    sub clear_password() {
        ubyte i
        for i in 0 to 63 network_mailbox.password[i]=0
    }
    sub leave() {
        clear_password()
        network_mailbox.focus=0
        state.wifi_step=0
        state.page=state.SETTINGS
    }
    sub back() {
        network_mailbox.focus=0
        clear_password()
        if state.wifi_step==0 leave()
        else if state.wifi_step==2 state.wifi_step=1
        else if state.wifi_step==3 and not state.wifi_host state.wifi_step=2
        else state.wifi_step=0
    }
    sub selected() {
        ubyte i
        if network_mailbox.selected>=network_mailbox.count return
        for i in 0 to 32 network_mailbox.ssid[i]=network_mailbox.character(network_mailbox.selected,i)
        clear_password()
        network_mailbox.focus=2
        state.wifi_step=2
    }
    sub demo() {
        state.source=0
        state.wifi_step=0
        network_mailbox.focus=0
        network_mailbox.action=5
        state.page=state.SETTINGS
    }
    sub modem() {
        state.wifi_host=false
        state.wifi_step=1
        network_mailbox.focus=0
        network_mailbox.action=1
    }
    sub primary() {
        network_mailbox.focus=0
        when state.wifi_step {
            0 -> demo()
            1 -> network_mailbox.action=1
            2 -> {
                if network_mailbox.ssid[0]==0 { network_mailbox.focus=1
                    void strings.copy(iso:"ENTER YOUR NETWORK NAME FIRST",network_mailbox.notice)
                    return }
                network_mailbox.action=3
            }
            3 -> network_mailbox.action=6
            4 -> network_mailbox.action=7
        }
    }
    sub field(ubyte y, ubyte focus, str value, bool secret) {
        ubyte i
        ubyte n=strings.length(value)
        ubyte start=0
        ubyte color=$16
        if network_mailbox.focus==focus color=$51
        ui.fill(11,y,58,3,color)
        if n>54 start=n-54
        if n>0 {
            for i in 0 to n-start-1 {
                if secret line[i]=42
                else line[i]=value[start+i]
            }
        }
        line[n-start]=0
        if network_mailbox.focus==focus {
            line[n-start]=95
            line[n-start+1]=0
        }
        ui.centered(11,y,58,3,color,line)
    }
    sub draw() {
        ubyte i
        ubyte n
        ubyte color
        ui.fill(0,8,80,52,$26)
        ui.fill(4,9,72,3,$45)
        ui.centered(4,9,59,3,$45,iso:"LET'S GET YOUR WEATHER CONNECTED")
        ui.centered(64,9,12,3,$45,iso:"[X] CLOSE")
        ui.text(10,14,$24,iso:"1 NETWORK       2 PASSWORD       3 WEATHER")
        if state.wifi_step==1 ui.text(10,14,$25,iso:"1 NETWORK")
        if state.wifi_step==2 ui.text(26,14,$25,iso:"2 PASSWORD")
        if state.wifi_step>=3 ui.text(43,14,$25,iso:"3 WEATHER")
        when state.wifi_step {
            0 -> {
                ui.text(10,16,$26,iso:"HOW ARE YOU USING WEATHER COMMANDER?")
                ui.card(8,19,64,10,iso:"1  EXPLORE THE OFFLINE DEMO  >")
                ui.text(11,22,$15,iso:"START WITH SAMPLE WEATHER")
                ui.text(11,25,$16,iso:"EXPLORE EVERY WEATHER SCREEN WITHOUT INTERNET.")
                ui.text(11,27,$14,iso:"RECORDED RADAR IS CLEARLY MARKED AS DEMO.")
                ui.card(8,32,64,10,iso:"2  ON A REAL COMMANDER X16  >")
                ui.text(11,35,$15,iso:"CONNECT MY WI-FI MODEM")
                ui.text(11,38,$16,iso:"WE'LL FIND YOUR NETWORK AND CONNECT TO WEATHER.")
                ui.text(11,40,$14,iso:"FOR THE TEXELEC / ZIMODEM WI-FI CARD.")
            }
            1 -> {
                ui.card(8,17,64,25,iso:"CHOOSE YOUR WI-FI NETWORK")
                for i in 0 to 9 {
                    if i>=network_mailbox.count break
                    for n in 0 to 32 line[n]=network_mailbox.character(i,n)
                    line[33]=0
                    color=$16
                    if i==network_mailbox.selected color=$51
                    ui.fill(10,20+i*2,60,2,color)
                    ui.centered(10,20+i*2,58,2,color,line)
                    ui.centered(68,20+i*2,2,2,color,iso:">")
                }
                if network_mailbox.count==0 {
                    if network_mailbox.connection==1 {
                        ui.text(12,23,$15,iso:"NO WI-FI MODEM WAS FOUND")
                        ui.text(12,26,$16,iso:"CHECK YOUR CARD, OR EXPLORE THE OFFLINE DEMO.")
                        ui.fill(12,32,56,3,$51)
                        ui.centered(12,32,56,3,$51,iso:"START WITH SAMPLE WEATHER >")
                    } else {
                        ui.text(12,23,$15,iso:"LET'S FIND YOUR NETWORK")
                        ui.text(12,26,$16,iso:"CLICK SCAN NETWORKS BELOW TO TRY AGAIN.")
                    }
                }
                ui.text(12,44,$25,iso:"HIDDEN NETWORK? ENTER ITS NAME >")
            }
            2 -> {
                ui.card(8,18,64,24,iso:"YOUR WI-FI DETAILS")
                ui.text(11,21,$14,iso:"NETWORK NAME")
                field(23,1,network_mailbox.ssid,false)
                ui.text(11,27,$14,iso:"WI-FI PASSWORD")
                field(29,2,network_mailbox.password,true)
                ui.text(11,33,$16,iso:"TYPE YOUR PASSWORD, THEN CLICK CONNECT.")
                ui.text(11,36,$14,iso:"CAPITAL LETTERS MATTER. OPEN NETWORK? LEAVE EMPTY.")
                ui.text(11,39,$14,iso:"YOUR PASSWORD IS NOT SAVED ON THE SD CARD.")
            }
            3 -> {
                ui.card(8,19,64,24,iso:"WI-FI CONNECTED / READY FOR WEATHER")
                ui.text(11,23,$15,iso:"YOUR X16 CONNECTS DIRECTLY TO PUBLIC APIS")
                ui.text(11,27,$16,iso:"OPEN-METEO: CURRENT WEATHER + FORECASTS")
                ui.text(11,30,$16,iso:"NOAA + PAGASA: CURRENT RADAR IMAGES")
                ui.text(11,34,$14,iso:"CLICK GET MY WEATHER TO LOAD YOUR STATIONS.")
                ui.text(11,38,$14,iso:"THE FIRST UPDATE MAY TAKE A MINUTE.")
            }
            4 -> {
                ui.card(8,19,64,23,iso:"YOU'RE CONNECTED!")
                ui.text(12,23,$15,iso:"YOUR WEATHER STATION IS READY")
                ui.text(12,27,$16,iso:"CURRENT WEATHER, CITY REPORTS AND FORECASTS")
                ui.text(12,30,$16,iso:"WILL UPDATE AUTOMATICALLY.")
                if state.radar_ready ui.text(12,34,$14,iso:"RADAR: LIVE FEED / OBSERVATION TIME SHOWN")
                else ui.text(12,34,$14,iso:"RADAR BUILDS IN THE BACKGROUND WHEN AVAILABLE")
                ui.text(12,38,$16,iso:"SAVE THESE SETTINGS AND LET'S WATCH THE WEATHER.")
            }
        }
        ui.fill(8,48,64,3,$16)
        ui.centered(8,48,64,3,$15,network_mailbox.notice)
        if network_mailbox.notice[0]==0 ui.centered(8,48,64,3,$14,iso:"CHOOSE A CONNECTION TO GET STARTED.")
        ui.fill(8,54,20,3,$45)
        if state.wifi_step==0 ui.centered(8,54,20,3,$45,iso:"< SETTINGS")
        else ui.centered(8,54,20,3,$45,iso:"< BACK")
        ui.fill(42,54,30,3,$51)
        when state.wifi_step {
            0 -> ui.centered(42,54,30,3,$51,iso:"OPEN DEMO >")
            1 -> ui.centered(42,54,30,3,$51,iso:"SCAN NETWORKS >")
            2 -> ui.centered(42,54,30,3,$51,iso:"CONNECT TO WI-FI >")
            3 -> ui.centered(42,54,30,3,$51,iso:"GET MY WEATHER >")
            4 -> ui.centered(42,54,30,3,$51,iso:"SAVE AND OPEN WEATHER >")
        }
        ui.centered(0,58,80,1,$24,iso:"CLICK TO CHOOSE / ENTER CONTINUES / ESC GOES BACK")
    }
    sub key() {
        ubyte ch=network_mailbox.key
        ubyte size
        ubyte limit
        uword fieldptr
        if ch==27 { back()
            return }
        if ch==9 {
            if state.wifi_step==2 {
                if network_mailbox.focus==1 network_mailbox.focus=2
                else network_mailbox.focus=1
            }
            return
        }
        if ch==13 {
            if network_mailbox.focus==1 { network_mailbox.focus=2
                return }
            if state.wifi_step==1 and network_mailbox.count>0 selected()
            else primary()
            return
        }
        if network_mailbox.focus!=0 {
            fieldptr=&network_mailbox.ssid
            limit=32
            if network_mailbox.focus==2 { fieldptr=&network_mailbox.password
                limit=63 }
            size=strings.length(fieldptr)
            if ch==20 or ch==8 { if size>0 @(fieldptr+size-1)=0
                return }
            if ch>=$c1 and ch<=$da ch-=$80
            else if ch>=65 and ch<=90 ch+=32
            if ch<32 or ch>126 or ch==34 return
            if network_mailbox.focus==1 and ch==44 return
            if size<limit { @(fieldptr+size)=ch
                @(fieldptr+size+1)=0 }
            return
        }
        if ch==88 or ch==120 { leave()
            return }
        if state.wifi_step==0 {
            if ch==49 demo()
            if ch==50 modem()
        }
        if state.wifi_step==1 {
            when ch {
                83,115 -> network_mailbox.action=1
                17 -> { if network_mailbox.selected+1<network_mailbox.count network_mailbox.selected++ }
                145 -> { if network_mailbox.selected>0 network_mailbox.selected-- }
                72,104 -> { state.wifi_step=2
                    network_mailbox.focus=1 }
            }
        }
    }
    sub hit() {
        ubyte row
        state.pointer_action=0
        state.pointer_target=0
        if interaction.inside(520,72,600,96) interaction.choose(7,0)
        if interaction.inside(64,432,224,456) interaction.choose(1,0)
        if interaction.inside(336,432,576,456) interaction.choose(4,0)
        when state.wifi_step {
            0 -> {
                if interaction.inside(64,152,576,232) interaction.choose(5,0)
                if interaction.inside(64,256,576,336) interaction.choose(6,0)
            }
            1 -> {
                if interaction.inside(80,160,560,320) {
                    row=((state.mouse_y-160)/16) as ubyte
                    if row<network_mailbox.count interaction.choose(2,row)
                }
                if network_mailbox.count==0 and network_mailbox.connection==1 and interaction.inside(96,256,544,280) interaction.choose(5,0)
                if interaction.inside(96,344,552,368) interaction.choose(8,0)
            }
            2 -> {
                if interaction.inside(88,168,552,208) interaction.choose(3,1)
                if interaction.inside(88,216,552,256) interaction.choose(3,2)
            }
        }
    }
    sub click() {
        hit()
        when state.pointer_action {
            1 -> back()
            2 -> { network_mailbox.selected=state.pointer_target
                selected() }
            3 -> network_mailbox.focus=state.pointer_target
            4 -> primary()
            5 -> demo()
            6 -> modem()
            7 -> leave()
            8 -> { state.wifi_step=2
                network_mailbox.focus=1 }
        }
    }
}
