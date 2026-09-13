%import ui
%import direct_render_mailbox
%import direct_png_mailbox
radar {
    extsub @bank 15 $a00f = restore_map()
    sub draw() {
        ubyte row
        ubyte col
        ubyte i
        uword source=$89f0
        restore_map()
        if state.radar_demo ui.heading(iso:"RADAR DEMO / NOT LIVE")
        else if state.country==1 ui.heading(iso:"PHILIPPINES RADAR / LIVE FEED")
        else ui.heading(iso:"USA RADAR / LIVE FEED")
        if state.radar_ready or state.radar_demo {
            for row in 0 to 27 {
                %asm {{ php
                    sei }}
                ui.at(18,12+row)
                for col in 0 to 83 {
                    cx16.VERA_DATA0=@(source)
                    source++
                }
                %asm {{ plp }}
            }
            if state.radar_demo {
                if state.status==3 ui.text(19,11,$25,iso:"DEMO / WAITING FOR FRESH RADAR")
                else ui.text(19,11,$25,iso:"RECORDED SAMPLE / CONNECT FOR LIVE DATA")
            }
            else if state.country==1 ui.text(19,11,$25,iso:"PAGASA / RAIN RATE / MM PER HOUR")
            else ui.text(19,11,$25,iso:"NOAA / BASE REFLECTIVITY")
            if state.country==1 {
                ui.text(21,16,$24,iso:"LUZON")
                ui.text(48,26,$24,iso:"VISAYAS")
                ui.text(47,35,$24,iso:"MINDANAO")
            }
            ui.fill(19,39,40,2,$16)
            if state.radar_demo {
                ui.text(19,39,$15,iso:"DEMO / NOT CURRENT")
                ui.text(43,39,$14,iso:"CONNECT [W]")
            } else {
                ui.text(20,39,$14,iso:"OBSERVED")
                ui.time(29,39,$16,@($7009),@($700a))
                ui.text(35,39,$14,iso:"LOCAL")
            }
            ui.text(19,40,$16,iso:"LIGHT")
            for i in 0 to 6 {
                ui.tile(25+i*2,40,258+(i as uword),$f0)
                ui.tile(26+i*2,40,258+(i as uword),$f0)
            }
            ui.text(40,40,$16,iso:"HEAVY")
            ui.text(49,40,$15,iso:"REFRESH >")
        } else {
            ui.heading(iso:"RADAR / FEED UNAVAILABLE")
            ui.text(19,11,$24,iso:"NATIONAL OVERVIEW / RADAR OFFLINE")
            ui.card(22,20,34,14,iso:"LET'S CHECK THE SKIES")
            if direct_render_mailbox.phase==1 {
                ui.text(24,23,$26,iso:"BUILDING YOUR RADAR MAP")
                ui.text(24,26,$24,iso:"YOU CAN EXPLORE OTHER SCREENS.")
                ui.text(24,28,$24,iso:"PH RADAR TAKES A FEW MINUTES.")
            } else {
                ui.text(24,23,$26,iso:"NO CURRENT RADAR IMAGE")
                ui.text(24,26,$24,iso:"RETRY OR CHECK WI-FI SETTINGS.")
                ui.text(24,28,$24,iso:"STALE IMAGES ARE NOT SHOWN.")
            }
            ui.button(24,31,12,2,$45,iso:"RETRY")
            ui.button(38,31,16,2,$51,iso:"CONNECT >")
            ui.text(20,39,$24,iso:"ACTUAL RADAR WHEN CONNECTED")
        }
    }
    sub animate() {
        ubyte width
        if direct_render_mailbox.phase!=1 or state.radar_ready or state.radar_demo return
        if direct_png_mailbox.height==0 return
        width=((direct_png_mailbox.row*28)/direct_png_mailbox.height) as ubyte
        ui.fill(24,29,28,1,$16)
        if width>0 ui.fill(24,29,width,1,$51)
    }
}
