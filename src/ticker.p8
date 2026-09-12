%import ui
%import strings
ticker {
    ubyte offset=0
    sub draw() {
        ubyte i
        ubyte idx
        uword headline=iso:"   CABLE WEATHER HEADLINES:  DEMO WEATHER / NOT LIVE  +++  WARMER TEMPERATURES MOVE INTO THE SOUTH THIS WEEK  +++  PRESS R TO REFRESH  +++"
        if state.status==1 headline=iso:"   CABLE WEATHER HEADLINES:  FILE SNAPSHOT LOADED / NOT A LIVE CONNECTION  +++  PRESS R TO RELOAD WCDATA.BIN  +++"
        if state.status==2 headline=iso:"   WEATHER UPDATE FAILED / DISPLAYING LAST AVAILABLE DATA  +++  CHECK WCDATA.BIN ON DEVICE 8  +++  PRESS R TO RETRY  +++"
        if state.extended and state.status==3 headline=$6368
        ubyte length=strings.length(headline)
        if offset>=length offset=0
        for i in 0 to 76 {
            idx=(offset+i) % length
            ui.cell(i+1,55,@(headline+idx),$26)
        }
        offset++
    }
}
