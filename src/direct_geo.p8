%import strings
%import state
%import network_mailbox
%import direct_http_mailbox
%import direct_json_mailbox
%import direct_time_mailbox
%import direct_crypto_mailbox
%import direct_weather_mailbox
%import direct_locations

direct_geo {
    extsub @bank 20 $a003 = http_get()
    extsub @bank 21 $a006 = json_validate()
    extsub @bank 21 $a009 = json_find()
    extsub @bank 21 $a00c = json_next()
    extsub @bank 21 $a00f = json_skip()
    extsub @bank 2 $a00c = integer_parse()
    extsub @bank 2 $a00f = integer_format()
    extsub @bank 22 $a003 = weather_fetch()
    extsub @bank 22 $a006 = weather_invalidate()
    &ubyte[64] request=$6b00
    ubyte[256] reply
    ubyte[40] previous
    ubyte[12] latitude
    ubyte[12] longitude
    ubyte[28] label
    uword id_low
    uword id_high
    uword cursor
    uword scope
    ubyte country
    bool valid
    str hex=iso:"0123456789ABCDEF"

    sub put(ubyte ch) {
        if cursor>=1023 { valid=false
            return }
        @($8000+cursor)=ch
        cursor++
    }
    sub append(str value) {
        ubyte i=0
        while value[i]!=0 { put(value[i])
            i++ }
    }
    sub field(str name) -> bool {
        direct_json_mailbox.scope=scope
        void strings.copy(name,direct_json_mailbox.key)
        json_find()
        return direct_json_mailbox.found and not direct_json_mailbox.error
    }
    sub coordinate(str name,uword destination,uword limit) -> bool {
        ubyte i
        ubyte ch
        uword whole=0
        bool fraction=false
        bool nonzero=false
        if not field(name) or direct_json_mailbox.kind!=6 or direct_json_mailbox.length>11 return false
        for i in 0 to direct_json_mailbox.length-1 {
            ch=direct_json_mailbox.text[i]
            if ch==45 and i==0 continue
            if ch==46 { fraction=true
                continue }
            if ch<48 or ch>57 return false
            if fraction { if ch!=48 nonzero=true }
            else { whole=whole*10+ch-48
                if whole>limit return false }
        }
        if whole==limit and nonzero return false
        void strings.copy(direct_json_mailbox.text,destination)
        return true
    }
    sub location() -> bool {
        ubyte i
        ubyte ch
        ubyte n
        if not field(iso:"country_code") or direct_json_mailbox.kind!=5 or direct_json_mailbox.length!=2 return false
        if country==0 {
            if direct_json_mailbox.text[0]!=85 or direct_json_mailbox.text[1]!=83 return false
        } else if direct_json_mailbox.text[0]!=80 or direct_json_mailbox.text[1]!=72 return false
        if not field(iso:"id") or direct_json_mailbox.kind!=6 return false
        integer_parse()
        if not direct_time_mailbox.valid return false
        id_low=direct_time_mailbox.low
        id_high=direct_time_mailbox.high
        if id_low==0 and id_high==0 return false
        if not coordinate(iso:"latitude",&latitude,90) or not coordinate(iso:"longitude",&longitude,180) return false
        if not field(iso:"name") or direct_json_mailbox.kind!=5 or direct_json_mailbox.length==0 return false
        n=0
        for i in 0 to 26 label[i]=0
        label[27]=0
        for i in 0 to direct_json_mailbox.length-1 {
            if n>=18 break
            ch=direct_json_mailbox.text[i]
            if ch<32 or ch>126 return false
            if ch>=97 and ch<=122 ch-=32
            label[n]=ch
            n++
        }
        if field(iso:"admin1") and direct_json_mailbox.kind==5 and direct_json_mailbox.length>0 {
            label[n]=44
            label[n+1]=32
            n+=2
            for i in 0 to direct_json_mailbox.length-1 {
                if n>=27 break
                ch=direct_json_mailbox.text[i]
                if ch<32 or ch>126 return false
                if ch>=97 and ch<=122 ch-=32
                label[n]=ch
                n++
            }
        }
        return true
    }
    sub message(ubyte status,str value) {
        reply[64]=status
        void strings.copy(value,&reply+66)
    }
    sub exchange() -> bool {
        ubyte i
        ubyte ch
        cursor=0
        valid=true
        void strings.copy(iso:"geocoding-api.open-meteo.com",direct_http_mailbox.host)
        if request[4]==1 {
            append(iso:"GET /v1/search?name=")
            for i in 8 to 55 {
                ch=request[i]
                if ch==0 break
                if ch>=65 and ch<=90 or ch>=97 and ch<=122 or ch>=48 and ch<=57 put(ch)
                else { put(37)
                    put(hex[ch>>4])
                    put(hex[ch & 15]) }
            }
            append(iso:"&count=5&language=en&format=json&countryCode=")
            if country==0 append(iso:"US")
            else append(iso:"PH")
        } else {
            append(iso:"GET /v1/get?id=")
            direct_time_mailbox.low=mkword(request[57],request[56])
            direct_time_mailbox.high=mkword(request[59],request[58])
            integer_format()
            append(direct_crypto_mailbox.timestamp)
        }
        append(iso:" HTTP/1.0\r\x0aHost: geocoding-api.open-meteo.com\r\x0aAccept-Encoding: identity\r\x0aConnection: close\r\x0a\r\x0a")
        if not valid return false
        direct_http_mailbox.request_length=cursor
        direct_http_mailbox.maximum=8192
        direct_http_mailbox.mode=0
        http_get()
        if not direct_http_mailbox.complete return false
        json_validate()
        return not direct_json_mailbox.error
    }
    sub search() {
        ubyte count=0
        uword resume
        uword destination
        scope=0
        if not field(iso:"results") {
            message(3,iso:"NO MATCHES / TRY CITY, STATE")
            return }
        if direct_json_mailbox.kind!=3 return
        json_next()
        while direct_json_mailbox.kind!=4 and not direct_json_mailbox.error {
            if direct_json_mailbox.kind!=1 or count>=5 return
            scope=direct_json_mailbox.start
            json_skip()
            resume=direct_json_mailbox.position
            if not location() return
            destination=&reply+96+(count as uword)*32
            @(destination)=lsb(id_low)
            @(destination+1)=msb(id_low)
            @(destination+2)=lsb(id_high)
            @(destination+3)=msb(id_high)
            void strings.copy(label,destination+4)
            count++
            direct_json_mailbox.position=resume
            json_next()
            if direct_json_mailbox.kind==11 json_next()
        }
        if direct_json_mailbox.error return
        if count==0 { message(3,iso:"NO MATCHES / TRY CITY, STATE")
            return }
        reply[65]=count
        message(1,iso:"CHOOSE YOUR CITY BELOW")
    }
    sub select() {
        ubyte i
        uword destination=$9890+(country as uword)*40
        bool was_set=@($98e0+country)!=0
        scope=0
        if not location() return
        if id_low!=mkword(request[57],request[56]) or id_high!=mkword(request[59],request[58]) return
        for i in 0 to 39 { previous[i]=@(destination+i)
            @(destination+i)=0 }
        void strings.copy(latitude,destination)
        void strings.copy(longitude,destination+12)
        for i in 0 to 14 {
            if label[i]==0 or label[i]==44 break
            @(destination+24+i)=label[i]
        }
        @($98e0+country)=1
        direct_weather_mailbox.country=country
        weather_invalidate()
        weather_fetch()
        if not network_mailbox.complete or network_mailbox.received!=1024 {
            for i in 0 to 39 @(destination+i)=previous[i]
            @($98e0+country)=was_set as ubyte
            weather_invalidate()
            message(4,iso:"WEATHER FAILED / CITY KEPT")
            return }
        message(2,iso:"CITY READY / SAVE IN SETTINGS")
    }
    sub send() {
        uword i
        uword checksum=0
        country=state.country
        for i in 0 to 255 reply[i as ubyte]=0
        for i in 0 to 63 reply[i as ubyte]=request[i as ubyte]
        message(4,iso:"NO CONNECTION / PLEASE RETRY")
        network_mailbox.complete=false
        network_mailbox.received=0
        for i in 0 to 59 checksum+=request[i as ubyte]
        if country>1 or request[0]!=87 or request[1]!=67 or request[2]!=67 or request[3]!=49 or checksum!=mkword(request[61],request[60]) return
        if state.source==0 message(4,iso:"CITY SEARCH NEEDS WI-FI MODE")
        else if request[4]==1 or request[4]==2 {
            if exchange() {
                if request[4]==1 search()
                else select()
            }
        }
        for i in 0 to 255 @($6400+i)=reply[i as ubyte]
        network_mailbox.complete=true
        network_mailbox.received=256
    }
}
