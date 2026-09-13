%import state
%import network_mailbox
%import direct_http_mailbox
%import direct_weather_mailbox
%import direct_locations
%import direct_stations
%import strings

direct_weather {
    extsub @bank 20 $a003 = http_get() clobbers(A,X,Y)
    extsub @bank 21 $a003 = decode_weather() clobbers(A,X,Y)
    ubyte[256] us0
    ubyte[256] us1
    ubyte[256] us2
    ubyte[256] us3
    ubyte[256] ph0
    ubyte[256] ph1
    ubyte[256] ph2
    ubyte[256] ph3
    uword[8] buffers=[&us0,&us1,&us2,&us3,&ph0,&ph1,&ph2,&ph3]
    bool[2] cached=[false,false]
    ubyte country
    ubyte city
    bool building
    uword ym
    uword dh
    uword ms
    uword jw
    uword cursor
    sub append(str text) {
        ubyte i=0
        while text[i]!=0 {
            if cursor>=1023 { building=false
                return }
            @(direct_http_mailbox.REQUEST+cursor)=text[i]
            cursor++
            i++
        }
    }
    sub custom() -> bool {
        if city!=0 return false
        if country==0 return direct_locations.us_set
        return direct_locations.ph_set
    }
    sub request() {
        uword index=(country as uword)*120+(city as uword)*12
        cursor=0
        building=true
        void strings.copy(iso:"api.open-meteo.com",direct_http_mailbox.host)
        append(iso:"GET /v1/forecast?latitude=")
        if custom() {
            if country==0 append(direct_locations.us_lat)
            else append(direct_locations.ph_lat)
        } else append(&direct_stations.latitude+index)
        append(iso:"&longitude=")
        if custom() {
            if country==0 append(direct_locations.us_lon)
            else append(direct_locations.ph_lon)
        } else append(&direct_stations.longitude+index)
        append(iso:"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,pressure_msl,wind_speed_10m,wind_direction_10m,visibility,dew_point_2m")
        append(iso:"&hourly=temperature_2m,weather_code,precipitation_probability,uv_index")
        append(iso:"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,sunrise,sunset")
        append(iso:"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=7&forecast_hours=25")
        append(iso:" HTTP/1.0\r\x0aHost: api.open-meteo.com\r\x0aUser-Agent: Weather-Commander-X16/0.2\r\x0aAccept-Encoding: identity\r\x0aConnection: close\r\x0a\r\x0a")
        direct_http_mailbox.request_length=cursor
        direct_http_mailbox.maximum=8192
        direct_http_mailbox.mode=0
    }
    sub copy_cache(bool save) {
        ubyte page
        uword i
        uword buffer
        for page in 0 to 3 {
            buffer=buffers[country*4+page]
            for i in 0 to 255 {
                if save @(buffer+i)=@($6400+(page as uword)*256+i)
                else @($6400+(page as uword)*256+i)=@(buffer+i)
            }
        }
    }
    sub fresh() -> bool {
        uword buffer=buffers[country*4]
        uword now_minutes
        uword before
        if not cached[country] return false
        ym,dh,ms,jw=cx16.clock_get_date_time()
        if @(buffer+10)!=lsb(ym) or @(buffer+11)!=msb(ym) or @(buffer+12)!=lsb(dh) return false
        now_minutes=(msb(dh) as uword)*60+lsb(ms)
        before=(@(buffer+13) as uword)*60+@(buffer+14)
        return now_minutes>=before and now_minutes-before<15
    }
    sub invalidate() {
        if direct_weather_mailbox.country<2 cached[direct_weather_mailbox.country]=false
    }
    sub header() {
        uword i
        uword checksum=0
        uword name=iso:"CHICAGO HOME"
        str headline=iso:"DIRECT WI-FI / OPEN-METEO MODEL WEATHER / CURRENT CONDITIONS + HOURLY + 7 DAYS / PUBLIC APIS / FORECASTS AT YOUR FINGERTIPS"
        @($6400)=87
        @($6401)=67
        @($6402)=87
        @($6403)=50
        @($6404)=2
        @($6405)=10
        @($6406)=1
        @($6407)=0
        ym,dh,ms,jw=cx16.clock_get_date_time()
        @($640a)=lsb(ym)
        @($640b)=msb(ym)
        @($640c)=lsb(dh)
        @($640d)=msb(dh)
        @($640e)=lsb(ms)
        @($640f)=country
        void strings.copy(headline,$6768)
        if country==0 and direct_locations.us_set name=&direct_locations.us_name
        if country==1 {
            name=iso:"MANILA HOME"
            if direct_locations.ph_set name=&direct_locations.ph_name
        }
        void strings.copy(name,$67e8)
        for i in 6 to 7 checksum+=@($6400+i)
        for i in 10 to 1023 checksum+=@($6400+i)
        @($6408)=lsb(checksum)
        @($6409)=msb(checksum)
    }
    sub fetch() {
        uword i
        network_mailbox.complete=false
        network_mailbox.received=0
        country=direct_weather_mailbox.country
        if country>1 return
        if fresh() {
            copy_cache(false)
            network_mailbox.complete=true
            network_mailbox.received=1024
            return
        }
        for i in 0 to 1023 @($6400+i)=0
        for city in 0 to 9 {
            request()
            if not building return
            http_get()
            if not direct_http_mailbox.complete return
            direct_weather_mailbox.city=city
            decode_weather()
            if not direct_weather_mailbox.valid return
        }
        header()
        copy_cache(true)
        cached[country]=true
        network_mailbox.complete=true
        network_mailbox.received=1024
    }
}
