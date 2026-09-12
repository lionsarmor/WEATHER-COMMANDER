; Shared ABI v1. Resident core ends below $9800. No pointers into another bank.
state {
    &ubyte page = $9800
    &ubyte city = $9801
    &ubyte units = $9802
    &ubyte interval = $9803
    &ubyte source = $9804
    &ubyte status = $9805       ; 0 demo, 1 file snapshot, 2 stale/error
    &ubyte cycles = $9806
    &ubyte sweep = $9807
    &bool automatic = $9808
    &ubyte text_bank = $9809
    &ubyte hour = $980a        ; local X16 RTC hour, consumed by station bank
    &ubyte home=$980b
    &bool extended=$980c
    &bool saved=$980d
    &bool radar_ready=$980e
    &uword mouse_x=$9810
    &uword mouse_y=$9812
    &ubyte forecast_mode=$9814
    &ubyte forecast_day=$9815
    &ubyte scenery=$9816
    &ubyte scene_bank=$9817
    &ubyte pointer_action=$9818
    &ubyte pointer_target=$9819
    &ubyte wifi_step=$981a
    &bool wifi_host=$981b
    &ubyte city_action=$981c
    &bool city_dirty=$981d
    &ubyte country=$981e       ; snapshot profile: 0 USA, 1 Philippines
    &ubyte country_choice=$981f
    &ubyte country_status=$9820 ; 0 idle, 1 loading, 2 failed, 3 snapshot ready
    &bool radar_demo=$9821     ; recorded sample, never a live observation
    &ubyte[80] records = $9840
    &ubyte[129] staging = $9900
    const ubyte HOME=0
    const ubyte NATIONAL=1
    const ubyte REGIONAL=2
    const ubyte LOCAL=3
    const ubyte RADAR=4
    const ubyte FORECAST=5
    const ubyte CITIES=6
    const ubyte SETTINGS=7
    const ubyte ABOUT=8
    const ubyte HELP=9
    const ubyte WIFI=10
    const ubyte ADD_CITY=11

    sub detail(ubyte offset) -> ubyte { return @($6020+(state.city as uword)*32+offset) }
    sub daily(ubyte day, ubyte offset) -> ubyte { return @($6160+(state.city as uword)*28+day*4+offset) }
    sub hourly(ubyte hour_index, ubyte offset) -> ubyte { return @($6278+(state.city as uword)*24+hour_index*3+offset) }

    sub field(ubyte station, ubyte offset) -> ubyte { return records[station*8+offset] }
    sub city_name(ubyte station) -> str {
        if country==1 and station!=0 {
            when station {
                1 -> return iso:"MANILA"
                2 -> return iso:"BAGUIO"
                3 -> return iso:"LEGAZPI"
                4 -> return iso:"PUERTO PRINCESA"
                5 -> return iso:"ILOILO"
                6 -> return iso:"CEBU"
                7 -> return iso:"TACLOBAN"
                8 -> return iso:"DAVAO"
                9 -> return iso:"ZAMBOANGA"
            }
        }
        when station {
            0 -> { if extended return $63e8
                   return iso:"METRO CITY" }
            1 -> return iso:"NEW YORK"
            2 -> return iso:"LOS ANGELES"
            3 -> return iso:"CHICAGO"
            4 -> return iso:"HOUSTON"
            5 -> return iso:"MIAMI"
            6 -> return iso:"DENVER"
            7 -> return iso:"SEATTLE"
            8 -> return iso:"BOSTON"
            9 -> return iso:"SAN FRANCISCO"
        }
        return iso:"UNKNOWN"
    }
    sub condition(ubyte value) -> str {
        when value {
            0 -> return iso:"CLEAR"
            1 -> return iso:"SUNNY"
            2 -> return iso:"CLOUDY"
            3 -> return iso:"RAIN"
            4 -> return iso:"SNOW"
            5 -> return iso:"STORMS"
            6 -> return iso:"FOG"
            7 -> return iso:"WINDY"
        }
        return iso:"--"
    }
}
