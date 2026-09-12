%import state
; One hit map drives both click dispatch and the pointer's hover feedback.
interaction {
    const ubyte KEY=1
    const ubyte PAGE=2
    const ubyte CITY=3
    const ubyte LOCAL_CITY=4
    const ubyte SCENE=5
    const ubyte FORECAST_TAB=6
    ubyte[9] xs=[21,20,24,32,40,36,49,51,49]
    ubyte[9] ys=[14,22,28,21,17,30,22,13,33]
    ubyte[9] stations=[7,9,2,6,3,4,1,8,5]
    sub inside(uword left, uword top, uword right, uword bottom) -> bool {
        return state.mouse_x>=left and state.mouse_x<right and state.mouse_y>=top and state.mouse_y<bottom
    }
    sub choose(ubyte action, ubyte target) {
        state.pointer_action=action
        state.pointer_target=target
    }
    sub resolve() {
        ubyte i
        ubyte row
        uword y
        state.pointer_action=0
        state.pointer_target=0
        if inside(320,332,472,348) { choose(PAGE,state.ADD_CITY)
            return }
        if inside(8,80,130,296) { choose(PAGE,((state.mouse_y-80)/24) as ubyte)
            return }
        if inside(8,454,632,472) {
            if state.mouse_x<104 choose(KEY,133)
            else if state.mouse_x<216 choose(KEY,137)
            else if state.mouse_x<320 choose(KEY,134)
            else if state.mouse_x<424 choose(KEY,138)
            else if state.mouse_x<536 choose(KEY,135)
            else choose(KEY,27)
            return
        }
        if inside(480,344,632,424) { choose(SCENE,0)
            return }
        if inside(16,352,240,432) or inside(248,352,472,432) {
            row=((state.mouse_y-352)/16) as ubyte
            if state.mouse_x>=248 row+=5
            choose(CITY,row)
            return
        }
        if inside(8,435,632,450) { choose(KEY,82)
            return }
        if inside(488,24,632,40) { choose(PAGE,state.WIFI)
            return }
        if inside(496,88,632,330) { choose(PAGE,state.LOCAL)
            return }
        when state.page {
            0 -> {
                if inside(160,112,304,264) choose(8,0)
                if inside(320,112,464,264) choose(8,1)
            }
            1 -> {
                if state.country==1 {
                    if inside(152,136,232,168) choose(LOCAL_CITY,1)
                    if inside(152,96,232,128) choose(LOCAL_CITY,2)
                    if inside(392,144,472,176) choose(LOCAL_CITY,3)
                    if inside(152,216,232,248) choose(LOCAL_CITY,4)
                    if inside(152,176,232,208) choose(LOCAL_CITY,5)
                    if inside(392,192,472,224) choose(LOCAL_CITY,6)
                    if inside(392,96,472,128) choose(LOCAL_CITY,7)
                    if inside(392,256,472,288) choose(LOCAL_CITY,8)
                    if inside(152,256,232,288) choose(LOCAL_CITY,9)
                    return
                }
                for i in 0 to 8 {
                    if inside((xs[i] as uword)*8,(ys[i] as uword)*8,(xs[i] as uword)*8+64,(ys[i] as uword)*8+24) {
                        choose(LOCAL_CITY,stations[i])
                        return
                    }
                }
                if not state.extended and inside(152,304,472,320) choose(PAGE,state.WIFI)
            }
            2 -> {
                for i in 0 to 2 {
                    y=120+(i as uword)*64
                    if inside(160,y,464,y+56) {
                        row=3
                        if i==1 row=6
                        if i==2 row=4
                        if state.country==1 {
                            row=1
                            if i==1 row=6
                            if i==2 row=8
                        }
                        choose(LOCAL_CITY,row)
                    }
                }
            }
            3,6 -> {
                if inside(160,312,240,328) choose(KEY,157)
                if inside(248,312,376,328) choose(PAGE,state.FORECAST)
                if inside(384,312,464,328) choose(KEY,29)
                if state.page==state.CITIES and inside(160,96,464,200) choose(PAGE,state.LOCAL)
                if state.page==state.CITIES and inside(160,288,464,304) choose(PAGE,state.LOCAL)
            }
            4 -> {
                if state.radar_ready or state.radar_demo {
                    if inside(392,312,464,328) choose(KEY,82)
                    if state.radar_demo and inside(344,304,456,320) choose(PAGE,state.WIFI)
                } else {
                    if inside(192,248,288,264) choose(KEY,82)
                    if inside(304,248,432,264) choose(PAGE,state.WIFI)
                }
            }
            5 -> {
                if state.extended and inside(160,112,464,128) {
                    if state.mouse_x<312 choose(FORECAST_TAB,0)
                    else choose(FORECAST_TAB,1)
                }
                if not state.extended and inside(160,296,464,320) choose(PAGE,state.WIFI)
            }
            7 -> {
                if inside(152,104,472,144) choose(KEY,87)
                if inside(152,152,472,176) choose(KEY,85)
                if inside(152,184,472,208) choose(KEY,84)
                if inside(152,216,472,240) choose(KEY,65)
                if inside(152,248,472,272) choose(KEY,68)
                if inside(152,280,472,296) choose(KEY,67)
                if inside(152,304,472,328) choose(KEY,83)
            }
            8 -> { if inside(160,312,464,328) choose(PAGE,state.HELP) }
            9 -> {
                if inside(160,152,464,176) choose(PAGE,state.LOCAL)
                if inside(160,216,464,240) choose(PAGE,state.FORECAST)
                if inside(160,240,464,264) choose(PAGE,state.SETTINGS)
                if inside(160,264,464,288) choose(KEY,82)
            }
        }
    }
}
