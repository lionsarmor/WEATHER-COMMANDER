%memtop $6000
%zeropage basicsafe
%import syslib
%import diskio
%import ui
%import textio
%import navigation
%import ticker
%import network_mailbox
%import interaction
%import direct_render_mailbox
%import direct_locations

main {
    extsub @bank 4 $a000 = station_init() clobbers(A,X,Y)
    extsub @bank 4 $a003 = station_draw() clobbers(A,X,Y)
    extsub @bank 5 $a000 = map_init() clobbers(A,X,Y)
    extsub @bank 5 $a003 = map_draw() clobbers(A,X,Y)
    extsub @bank 5 $a006 = local_draw() clobbers(A,X,Y)
    extsub @bank 6 $a000 = conditions_init() clobbers(A,X,Y)
    extsub @bank 6 $a003 = conditions_draw() clobbers(A,X,Y)
    extsub @bank 7 $a000 = cities_init() clobbers(A,X,Y)
    extsub @bank 7 $a003 = cities_draw() clobbers(A,X,Y)
    extsub @bank 7 $a006 = city_panel() clobbers(A,X,Y)
    extsub @bank 8 $a000 = forecast_init() clobbers(A,X,Y)
    extsub @bank 8 $a003 = forecast_draw() clobbers(A,X,Y)
    extsub @bank 9 $a000 = radar_init() clobbers(A,X,Y)
    extsub @bank 9 $a003 = radar_draw() clobbers(A,X,Y)
    extsub @bank 9 $a006 = radar_animate() clobbers(A,X,Y)
    extsub @bank 10 $a000 = settings_init() clobbers(A,X,Y)
    extsub @bank 10 $a003 = settings_draw() clobbers(A,X,Y)
    extsub @bank 11 $a000 = about_init() clobbers(A,X,Y)
    extsub @bank 11 $a003 = about_draw() clobbers(A,X,Y)
    extsub @bank 11 $a006 = help_draw() clobbers(A,X,Y)
    extsub @bank 13 $a000 = provider_init() clobbers(A,X,Y)
    extsub @bank 13 $a003 = provider_refresh() clobbers(A,X,Y)
    extsub @bank 13 $a006 = provider_age() clobbers(A,X,Y)
    extsub @bank 12 $a000 = network_init() clobbers(A,X,Y)
    extsub @bank 12 $a003 = network_action() clobbers(A,X,Y)
    extsub @bank 14 $a000 = wifi_init() clobbers(A,X,Y)
    extsub @bank 14 $a003 = wifi_draw() clobbers(A,X,Y)
    extsub @bank 14 $a006 = wifi_key() clobbers(A,X,Y)
    extsub @bank 14 $a009 = wifi_click() clobbers(A,X,Y)
    extsub @bank 14 $a00c = wifi_hit() clobbers(A,X,Y)
    extsub @bank 15 $a000 = radar_feed_init() clobbers(A,X,Y)
    extsub @bank 15 $a003 = radar_feed_refresh() clobbers(A,X,Y)
    extsub @bank 15 $a006 = radar_feed_age() clobbers(A,X,Y)
    extsub @bank 16 $a000 = preferences_init() clobbers(A,X,Y)
    extsub @bank 16 $a003 = preferences_load() clobbers(A,X,Y)
    extsub @bank 16 $a006 = preferences_save() clobbers(A,X,Y)
    extsub @bank 17 $a000 = city_input_init() clobbers(A,X,Y)
    extsub @bank 17 $a003 = city_input_draw() clobbers(A,X,Y)
    extsub @bank 17 $a006 = city_input_key() clobbers(A,X,Y)
    extsub @bank 17 $a009 = city_input_hit() clobbers(A,X,Y)
    extsub @bank 17 $a00c = city_input_click() clobbers(A,X,Y)
    extsub @bank 17 $a00f = city_input_send() clobbers(A,X,Y)
    extsub @bank 17 $a012 = city_input_tick() clobbers(A,X,Y)

    extsub @bank 18 $a000 = home_init() clobbers(A,X,Y)
    extsub @bank 18 $a003 = home_draw() clobbers(A,X,Y)
    extsub @bank 18 $a006 = home_choose() clobbers(A,X,Y)
    extsub @bank 18 $a009 = home_tick() clobbers(A,X,Y)

    extsub @bank 19 $a000 = banner_init() clobbers(A,X,Y)
    extsub @bank 19 $a003 = banner_draw() clobbers(A,X,Y)

    extsub @bank 1 $a000 = direct_radar_init()
    extsub @bank 2 $a000 = direct_crypto_init()
    extsub @bank 3 $a000 = direct_png_init()
    extsub @bank 20 $a000 = direct_http_init()
    extsub @bank 21 $a000 = direct_decode_init()
    extsub @bank 22 $a000 = direct_weather_init()
    extsub @bank 23 $a000 = direct_render_init()
    extsub @bank 24 $a000 = direct_inflate_init()
    extsub @bank 15 $a009 = radar_feed_step()
    extsub @bank 15 $a00c = radar_feed_cancel()
    extsub @bank 15 $a00f = radar_feed_restore()
    ubyte radar_phase
    uword now
    uword last_refresh
    uword last_clock
    uword last_ticker
    uword last_sweep
    uword last_scene
    ubyte scene_loaded=255
    bool pointer_hot=false
    ubyte key
    ubyte buttons
    ubyte old_buttons=0
    uword mx
    uword my
    byte wheel
    bool running=true
    ubyte background=255
    uword missing

    ; Preserve all palette entries, including the mouse palette, for BASIC.
    sub save_palette() {
        uword offset
        for offset in 0 to 511 @($9a00+offset)=cx16.vpeek(1,$fa00+offset)
        for offset in 0 to 6 @($9c00+offset)=@($9f34+offset)
    }
    sub restore_palette() {
        uword offset
        for offset in 0 to 511 cx16.vpoke(1,$fa00+offset,@($9a00+offset))
    }
    sub restore_screen() {
        uword offset
        restore_palette()
        cx16.VERA_CTRL=0
        for offset in 0 to 6 @($9f34+offset)=@($9c00+offset)
        cx16.VERA_DC_VIDEO=$21
        cx16.set_screen_mode(0)
        cx16.screen_set_charset(2,0)
        cbm.CHROUT(147)
        cbm.CHROUT(5)
    }
    sub load_bank(str filename, ubyte bank) -> bool {
        uword result
        missing=filename
        cx16.rambank(bank)
        result=diskio.loadlib(filename,$a000)
        cx16.rambank(0)
        return result!=0
    }
    sub load_vram(str filename, ubyte bank, uword address) -> bool {
        missing=filename
        return diskio.vload_raw(filename,bank,address)
    }
    sub load_all() -> bool {
        ubyte i
        str scene_file=iso:"WCSC00.BIN"
        if not load_bank(iso:"WCRAPI.BIN",1) return false
        if not load_bank(iso:"WCHASH.BIN",2) return false
        if not load_bank(iso:"WCPNG.BIN",3) return false
        if not load_bank(iso:"WCHTTP.BIN",20) return false
        if not load_bank(iso:"WCJSON.BIN",21) return false
        if not load_bank(iso:"WCWEATH.BIN",22) return false
        if not load_bank(iso:"WCRMAKE.BIN",23) return false
        if not load_bank(iso:"WCZLIB.BIN",24) return false
        if not load_bank(iso:"WCIDENT.BIN",4) return false
        if not load_bank(iso:"WCGEOG.BIN",5) return false
        if not load_bank(iso:"WCCOND.BIN",6) return false
        if not load_bank(iso:"WCCITY.BIN",7) return false
        if not load_bank(iso:"WCFCST.BIN",8) return false
        if not load_bank(iso:"WCRADAR.BIN",9) return false
        if not load_bank(iso:"WCSET.BIN",10) return false
        if not load_bank(iso:"WCABOUT.BIN",11) return false
        if not load_bank(iso:"WCPROV.BIN",13) return false
        if not load_bank(iso:"WCNET.BIN",12) return false
        if not load_bank(iso:"WCWIFI.BIN",14) return false
        if not load_bank(iso:"WCRFEED.BIN",15) return false
        if not load_bank(iso:"WCPREF.BIN",16) return false
        if not load_bank(iso:"WCADD.BIN",17) return false
        if not load_bank(iso:"WCHOME.BIN",18) return false
        if not load_bank(iso:"WCBANNER.BIN",19) return false
        if not load_bank(iso:"WCHART.BIN",30) return false
        if not load_bank(iso:"WCPH.BIN",31) return false
        if not load_bank(iso:"WCNAT.BIN",32) return false
        if not load_bank(iso:"WCREG.BIN",33) return false
        if not load_bank(iso:"WCRAD.BIN",34) return false
        if not load_bank(iso:"WCBLK.BIN",35) return false
        for i in 0 to 27 {
            scene_file[4]=48+i/10
            scene_file[5]=48+i % 10
            if not load_bank(scene_file,36+i) return false
        }
        if not load_vram(iso:"WCTILES.BIN",0,0) return false
        if not load_vram(iso:"WCMAP.BIN",0,$8000) return false
        if not load_vram(iso:"WCFONT.BIN",1,0) return false
        if not load_vram(iso:"WCPAL.BIN",1,$fa00) return false
        if not load_vram(iso:"WCPOINTER.BIN",1,$8000) return false
        return true
    }
    sub video() {
        cx16.VERA_CTRL=0
        cx16.VERA_DC_HSCALE=128
        cx16.VERA_DC_VSCALE=128
        cx16.VERA_L0_CONFIG=$62  ; 128x64, 4bpp tiles
        cx16.VERA_L0_MAPBASE=$40
        cx16.VERA_L0_TILEBASE=0
        cx16.VERA_L0_HSCROLL_L=0
        cx16.VERA_L0_HSCROLL_H=0
        cx16.VERA_L0_VSCROLL_L=0
        cx16.VERA_L0_VSCROLL_H=0
        cx16.VERA_L1_CONFIG=$62  ; 128x64, 4bpp glyph tiles
        cx16.VERA_L1_MAPBASE=$60
        cx16.VERA_L1_TILEBASE=$80
        cx16.VERA_L1_HSCROLL_L=0
        cx16.VERA_L1_HSCROLL_H=0
        cx16.VERA_L1_VSCROLL_L=0
        cx16.VERA_L1_VSCROLL_H=0
        ui.fill(0,0,80,60,0)
        cx16.VERA_DC_VIDEO=$71  ; VGA, both layers, sprites
        cx16.mouse_config(-1,80,60)
        cx16.mouse_set_sprite_offset(0,-7)
        cx16.vpoke(1,$fc00,0)    ; sprite pixels at $18000, 4bpp
        cx16.vpoke(1,$fc01,$0c)
        cx16.vpoke(1,$fc06,$0c)  ; in front of both layers
        cx16.vpoke(1,$fc07,$a0)  ; 32x32, artwork palette
    }
    sub scene_update() {
        uword source=$a000
        uword destination=$6000
        ubyte chunk
        ubyte i
        station_draw()
        if scene_loaded==state.scene_bank return
        cx16.rambank(state.scene_bank)
        for chunk in 0 to 189 {
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=lsb(destination)
            cx16.VERA_ADDR_M=msb(destination)
            cx16.VERA_ADDR_H=$10
            for i in 0 to 31 {
                cx16.VERA_DATA0=@(source)
                source++
            }
            %asm {{ plp }}
            destination+=32
        }
        cx16.rambank(0)
        scene_loaded=state.scene_bank
    }
    sub next_scene() {
        state.scenery=(state.scenery+1) % 7
        scene_update()
        last_scene=cbm.RDTIM16()
    }
    sub set_background() {
        ubyte bank=35
        ubyte row
        ubyte col
        uword src=$a002
        uword dst=$8b24  ; artwork tile x18,y11 (preserve the frame)
        if state.page==state.NATIONAL and state.country==0 bank=32
        if state.page==state.REGIONAL bank=35
        if state.page==state.RADAR and state.country==0 bank=34
        if bank==background return
        cx16.rambank(bank)
        for row in 0 to 29 {
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=lsb(dst)
            cx16.VERA_ADDR_M=msb(dst)
            cx16.VERA_ADDR_H=$10
            for col in 0 to 83 {
                cx16.VERA_DATA0=@(src)
                src++
            }
            %asm {{ plp }}
            src+=4
            dst+=256
        }
        cx16.rambank(0)
        background=bank
    }
    sub country_art() {
        ubyte row
        ubyte col
        uword source=$a000
        if state.page==state.HOME cx16.rambank(30)
        else if (state.page==state.NATIONAL or state.page==state.RADAR) and state.country==1 cx16.rambank(31)
        else return
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
        cx16.rambank(0)
    }
    sub draw_center() {
        set_background()
        ui.clear_center()
        country_art()
        when state.page {
            0 -> home_draw()
            1,2 -> map_draw()
            3 -> local_draw()
            4 -> radar_draw()
            5 -> forecast_draw()
            6 -> city_panel()
            7 -> settings_draw()
            8 -> about_draw()
            9 -> help_draw()
            11 -> city_input_draw()
        }
    }
    sub clock_draw() {
        provider_age()
        uword ym
        uword dh
        uword ms
        uword jw
        ubyte hour
        uword year
        bool radar_was_ready
        ubyte month
        ubyte i
        ubyte n
        str months=iso:"JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC"
        str date=iso:"SEP 11, 2026  08:46 PM LOCAL"
        &ubyte[32] location=$6d40
        ubyte[8] country
        ubyte[32] status
        ym,dh,ms,jw=cx16.clock_get_date_time()
        radar_was_ready=state.radar_ready
        radar_feed_age()
        if radar_was_ready and not state.radar_ready and state.page==state.RADAR draw_center()
        year=1900+lsb(ym)
        month=msb(ym)
        if month<1 or month>12 month=1
        for i in 0 to 2 date[i]=months[(month-1)*3+i]
        date[4]=lsb(dh)/10+48
        date[5]=lsb(dh) % 10+48
        date[8]=(year/1000) as ubyte+48
        date[9]=(year/100 % 10) as ubyte+48
        date[10]=(year/10 % 10) as ubyte+48
        date[11]=(year % 10) as ubyte+48
        hour=msb(dh)
        state.hour=hour
        scene_update()
        date[20]=65
        if hour>=12 date[20]=80
        hour=hour % 12
        if hour==0 hour=12
        date[14]=hour/10+48
        if hour<10 date[14]=32
        date[15]=hour % 10+48
        date[17]=lsb(ms)/10+48
        date[18]=lsb(ms) % 10+48
        date[22]=0
        void strings.copy(date,$6d20)
        void strings.copy(state.city_name(state.city),location)
        n=strings.length(location)
        if state.country==1 void strings.copy(iso:" / PH",country)
        else void strings.copy(iso:" / USA",country)
        ; A personal city may be anywhere in the world, outside this map profile.
        if state.city!=0 {
            for i in 0 to strings.length(country) location[n+i]=country[i]
        }
        banner_draw()
        void strings.copy(iso:"ONLINE / DEG F / CLOCK LOCAL",status)
        if state.status==0 void strings.copy(iso:"DEMO / DEG F / CLOCK LOCAL",status)
        if state.status==2 void strings.copy(iso:"STALE / DEG F / CLOCK LOCAL",status)
        for i in 1 to strings.length(status)-1 {
            if status[i]==70 and status[i-1]==32 {
                if state.units==1 status[i]=67
            }
        }
        ui.fill(8,4,34,1,$24)
        ui.centered(8,4,34,1,$24,status)
    }
    sub redraw() {
        state.text_bank=1-state.text_bank
        ui.fill(0,0,80,60,0)
        navigation.draw()
        draw_center()
        conditions_draw()
        cities_draw()
        clock_draw()
        if state.page==state.WIFI wifi_draw()
        if state.page!=state.WIFI ticker.draw()
        if state.text_bank==0 cx16.VERA_L1_MAPBASE=$60
        else cx16.VERA_L1_MAPBASE=$d8
    }
    sub refresh() {
        if state.source==0 radar_feed_cancel()
        provider_refresh()
        radar_feed_refresh()
        last_refresh=cbm.RDTIM16()
        redraw()
    }
    sub change_city(bool next) {
        if next {
            state.city++
            if state.city>9 state.city=0
        } else {
            if state.city==0 state.city=9
            else state.city--
        }
        conditions_draw()
        cities_draw()
        clock_draw()
        draw_center()
    }
    sub select_country() {
        home_choose()
        finish_country()
        redraw()
    }
    sub finish_country() {
        if state.country_status!=3 return
        radar_feed_cancel()
        state.city_action=3
        provider_refresh()
        state.city_action=0
        if state.extended and state.country==state.country_choice {
            state.saved=false
            state.city=0
            state.home=0
            state.country_status=0
            state.page=state.NATIONAL
        } else state.country_status=2
        radar_feed_refresh()
        last_refresh=cbm.RDTIM16()
    }
    sub handle_key() {
        if state.country_status==1 return
        if state.page==state.HOME and (key==49 or key==50) {
            state.country_choice=key-49
            select_country()
            return
        }
        if state.page==state.ADD_CITY {
            network_mailbox.key=key
            city_input_key()
            finish_city_action()
            return
        }
        if state.page==state.WIFI {
            network_mailbox.key=key
            wifi_key()
            finish_wifi_action()
            return
        }
        if state.page==state.SETTINGS and key!=83 and key!=115 state.saved=false
        when key {
            27 -> running=false
            133 -> state.page=state.HELP
            137 -> state.page=state.CITIES
            134 -> state.page=state.FORECAST
            138 -> state.page=state.RADAR
            135 -> state.page=state.SETTINGS
            72,104 -> state.page=state.HOME
            78,110 -> state.page=state.ADD_CITY
            87,119 -> { if state.page==state.SETTINGS or state.page==state.RADAR state.page=state.WIFI }
            83,115 -> { if state.page==state.SETTINGS preferences_save() }
            67,99 -> { if state.page==state.SETTINGS { state.home=state.city
                    state.saved=false } }
            70,102 -> { if state.page==state.FORECAST state.forecast_mode=1-state.forecast_mode }
            71,103 -> { next_scene()
                return }
            82,114 -> { radar_feed_cancel()
            refresh()
            return }
            29 -> { change_city(true)
            return }
            157 -> { change_city(false)
            return }
            17,9 -> { state.page++
            if state.page>8 state.page=0 }
            145 -> { if state.page==0 state.page=8
            else state.page-- }
            13 -> state.page=state.LOCAL
            85,117 -> { if state.page==state.SETTINGS state.units=1-state.units }
            84,116 -> {
                if state.page==state.SETTINGS {
                    if state.interval==30 state.interval=60
                    else if state.interval==60 state.interval=120
                    else state.interval=30
                    last_refresh=cbm.RDTIM16()
                }
            }
            65,97 -> { if state.page==state.SETTINGS state.automatic=not state.automatic }
            68,100 -> {
                if state.page==state.SETTINGS {
                    state.source=2-state.source
                    radar_feed_cancel()
                    refresh()
                    return
                }
            }
            else -> return
        }
        redraw()
    }
    sub handle_mouse() {
        if state.country_status==1 return
        state.mouse_x=mx
        state.mouse_y=my
        if state.page==state.WIFI { wifi_click()
            finish_wifi_action()
            return }
        if state.page==state.ADD_CITY {
            interaction.resolve()
            city_input_hit()
            if state.pointer_action==7 {
                city_input_click()
                finish_city_action()
                return
            }
        }
        interaction.resolve()
        when state.pointer_action {
            1 -> { key=state.pointer_target
                handle_key()
                return }
            2 -> {
                key=state.pointer_target
                if state.page==state.ADD_CITY {
                    network_mailbox.key=27
                    city_input_key()
                }
                state.page=key
            }
            3 -> state.city=state.pointer_target
            4 -> { state.city=state.pointer_target
                state.page=state.LOCAL }
            5 -> { next_scene()
                return }
            6 -> state.forecast_mode=state.pointer_target
            8 -> { state.country_choice=state.pointer_target
                select_country()
                return }
            else -> return
        }
        redraw()
    }
    sub pointer_update() {
        bool hot
        state.mouse_x=mx
        state.mouse_y=my
        if state.page==state.WIFI wifi_hit()
        else if state.page==state.ADD_CITY { interaction.resolve()
            city_input_hit() }
        else interaction.resolve()
        hot=state.pointer_action!=0
        if hot!=pointer_hot {
            if hot cx16.vpoke(1,$fc00,$10)
            else cx16.vpoke(1,$fc00,0)
            pointer_hot=hot
        }
    }
    sub finish_city_action() {
        if state.city_action==1 or state.city_action==2 {
            redraw()
            city_input_send()
        }
        if state.city_action==3 {
            provider_refresh()
            state.city_action=0
        }
        state.city_dirty=false
        redraw()
    }
    sub finish_wifi_action() {
        state.saved=false
        if network_mailbox.action!=0 {
            void strings.copy(iso:"WORKING... PLEASE WAIT",network_mailbox.notice)
            if network_mailbox.action==1 void strings.copy(iso:"LOOKING FOR WI-FI NETWORKS...",network_mailbox.notice)
            if network_mailbox.action==3 void strings.copy(iso:"CONNECTING TO YOUR WI-FI...",network_mailbox.notice)
            if network_mailbox.action==6 void strings.copy(iso:"LOADING YOUR WEATHER...",network_mailbox.notice)
            redraw()
            if network_mailbox.action==6 {
                network_mailbox.action=0
                state.source=2
                network_mailbox.notice[0]=0
                provider_refresh()
                last_refresh=cbm.RDTIM16()
                if state.status==3 {
                    radar_feed_refresh()
                    state.wifi_step=4
                    state.automatic=true
                    void strings.copy(iso:"CONNECTED / YOUR WEATHER IS UP TO DATE",network_mailbox.notice)
                } else {
                    radar_feed_restore()
                    if network_mailbox.notice[0]==0 void strings.copy(iso:"NO FRESH WEATHER YET / PLEASE RETRY",network_mailbox.notice)
                }
            } else if network_mailbox.action==7 {
                network_mailbox.action=0
                preferences_save()
                if state.saved { state.wifi_step=0
                    state.page=state.HOME }
                else void strings.copy(iso:"WEATHER READY / COULD NOT SAVE SETTINGS",network_mailbox.notice)
            } else {
                if network_mailbox.action==5 {
                    radar_feed_cancel()
                    network_action()
                    provider_refresh()
                    radar_feed_refresh()
                } else network_action()
                if state.wifi_step==2 and network_mailbox.connection==3 {
                    state.wifi_step=3
                    network_mailbox.focus=0
                }
            }
        }
        redraw()
    }
    sub service_timers() {
        now=cbm.RDTIM16()
        if now-last_clock>=60 { clock_draw()
        if state.country_status==1 {
            home_tick()
            if state.country_status!=1 { finish_country()
                redraw() }
        }
        if state.page==state.ADD_CITY {
            city_input_tick()
            if state.city_dirty finish_city_action()
        }
        last_clock=now }
        if now-last_ticker>=10 { if state.page!=state.WIFI ticker.draw()
        last_ticker=now }
        if now-last_sweep>=12 {
            state.sweep=(state.sweep+1) % 40
            if state.page==state.RADAR radar_animate()
            last_sweep=now
        }
        now=cbm.RDTIM16()
        if now-last_scene>=1800 next_scene()
        if state.automatic and now-last_refresh >= (state.interval as uword)*60 refresh()
    }
    sub start() {
        cx16.set_screen_mode(0)
        save_palette()
        txt.print(iso:"WEATHER COMMANDER - LOADING BANKS...\r\n")
        cx16.VERA_CTRL=0
        cx16.VERA_DC_VIDEO=1
        if not load_all() {
            restore_screen()
            txt.print(iso:"WEATHER COMMANDER: MISSING OR UNREADABLE FILE\r\n")
            txt.print(missing)
            txt.print(iso:"\r\nCOPY ALL DIST/SDCARD FILES TO DEVICE 8.\r\n")
            return
        }
        direct_radar_init()
        direct_crypto_init()
        direct_png_init()
        direct_http_init()
        direct_decode_init()
        direct_weather_init()
        direct_render_init()
        direct_inflate_init()
        direct_locations.us_set=false
        direct_locations.ph_set=false
        station_init()
        map_init()
        conditions_init()
        cities_init()
        forecast_init()
        radar_init()
        settings_init()
        about_init()
        provider_init()
        network_init()
        wifi_init()
        radar_feed_init()
        preferences_init()
        city_input_init()
        home_init()
        banner_init()
        network_mailbox.initialize()
        state.page=0
        state.text_bank=0
        state.city=0
        state.units=0
        state.interval=60
        state.source=2
        state.status=0
        state.cycles=0
        state.sweep=0
        state.automatic=true
        state.home=0
        state.extended=false
        state.radar_ready=false
        state.radar_demo=false
        state.forecast_mode=0
        state.scenery=0
        state.scene_bank=255
        state.wifi_step=0
        state.wifi_host=false
        state.saved=false
        state.city_action=0
        state.city_dirty=false
        state.country=0
        state.country_choice=0
        state.country_status=0
        preferences_load()
        provider_refresh()
        radar_feed_refresh()
        video()
        redraw()
        cbm.kbdbuf_clear()
        last_refresh=cbm.RDTIM16()
        last_clock=last_refresh
        last_ticker=last_refresh
        last_sweep=last_refresh
        last_scene=last_refresh
        while running {
            sys.waitvsync()
            now=cbm.RDTIM16()
            key=cbm.GETIN2()
            if key!=0 handle_key()
            buttons,mx,my,wheel=cx16.mouse_pos()
            if buttons&1 != 0 and old_buttons&1 == 0 handle_mouse()
            old_buttons=buttons
            pointer_update()
            radar_phase=direct_render_mailbox.phase
            radar_feed_step()
            if radar_phase!=direct_render_mailbox.phase and state.page==state.RADAR draw_center()
            service_timers()
        }
        radar_feed_cancel()
        cx16.mouse_config(0,0,0)
        restore_screen()
        txt.print(iso:"WEATHER COMMANDER CLOSED.\r\n")
    }
}
