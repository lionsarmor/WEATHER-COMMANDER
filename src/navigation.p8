%import ui
navigation {
    sub draw() {
        ubyte i
        ubyte color
        ubyte x
        for i in 0 to 8 {
            color=$14
            if i == state.page color=$51
            ui.fill(4,10+i*3,12,3,0)
            if i==state.page {
                for x in 4 to 15 {
                    ui.cell(x,10+i*3,188,color)
                    ui.cell(x,12+i*3,189,color)
                }
                ui.fill(4,11+i*3,12,1,color)
            }
            ui.centered(4,11+i*3,12,1,color,label(i))
        }
        ; One shortcut row, with a blank bottom margin below its centered labels.
        ui.fill(0,57,80,3,$16)
        ui.button(1,57,4,2,$e1,iso:"F1")
        ui.centered(6,57,7,2,$16,iso:"HELP")
        ui.button(14,57,4,2,$e1,iso:"F2")
        ui.centered(19,57,8,2,$16,iso:"CITIES")
        ui.button(28,57,4,2,$e1,iso:"F3")
        ui.centered(33,57,7,2,$16,iso:"FCST")
        ui.button(41,57,4,2,$e1,iso:"F4")
        ui.centered(46,57,7,2,$16,iso:"RADAR")
        ui.button(54,57,4,2,$e1,iso:"F5")
        ui.centered(59,57,8,2,$16,iso:"SETUP")
        ui.button(68,57,5,2,$e1,iso:"ESC")
        ui.centered(74,57,5,2,$16,iso:"EXIT")
    }
    sub label(ubyte page) -> str {
        when page {
            0 -> return iso:"HOME"
            1 -> return iso:"NATIONAL"
            2 -> return iso:"REGIONAL"
            3 -> return iso:"LOCAL"
            4 -> return iso:"RADAR"
            5 -> return iso:"FORECAST"
            6 -> return iso:"CITIES"
            7 -> return iso:"SETTINGS"
        }
        return iso:"ABOUT"
    }
}
