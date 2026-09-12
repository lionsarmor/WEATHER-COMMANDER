%import syslib
%import strings
%import direct_radar_mailbox
%import direct_http_mailbox
%import direct_json_mailbox
%import direct_crypto_mailbox
%import direct_time_mailbox
%import direct_radar_projection

direct_radar {
    extsub @bank 20 $a003 = http_get()
    extsub @bank 21 $a006 = json_validate()
    extsub @bank 21 $a009 = json_find()
    extsub @bank 21 $a00c = json_next()
    extsub @bank 21 $a00f = json_skip()
    extsub @bank 2 $a003 = hmac()
    extsub @bank 2 $a009 = utc_date()
    extsub @bank 2 $a00c = epoch_parse()
    extsub @bank 2 $a00f = epoch_format()
    ubyte[41] csrf
    ubyte[96] grant
    ubyte[12] version
    ubyte[12] raster
    uword cursor
    uword scope
    uword path
    str digits=iso:"0123456789abcdef"
    str us_host=iso:"mapservices.weather.noaa.gov"
    str ph_host=iso:"panahon.gov.ph"
    str us_service=iso:"/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer"

    sub fail(ubyte error) {
        if direct_radar_mailbox.error==0 direct_radar_mailbox.error=error
        direct_radar_mailbox.downloaded=false
    }
    sub put(ubyte value) {
        if cursor>=4095 { fail(1)
            return }
        @(direct_http_mailbox.REQUEST+cursor)=value
        cursor++
    }
    sub append(str text) {
        ubyte i=0
        while text[i]!=0 {
            put(text[i])
            if i==255 { fail(1)
                return }
            i++
        }
    }
    sub begin() {
        cursor=0
        if direct_radar_mailbox.country==0 void strings.copy(us_host,direct_http_mailbox.host)
        else void strings.copy(ph_host,direct_http_mailbox.host)
        append(iso:"GET ")
    }
    sub headers(bool signed) {
        ubyte i
        append(iso:" HTTP/1.1\r\x0aHost: ")
        append(direct_http_mailbox.host)
        append(iso:"\r\x0aUser-Agent: Weather-Commander-X16/0.2\r\x0aAccept-Encoding: identity\r\x0aConnection: close\r\x0a")
        if signed {
            append(iso:"Referer: https://panahon.gov.ph/\r\x0aX-Ts: ")
            append(direct_crypto_mailbox.timestamp)
            append(iso:"\r\x0aX-Nonce: ")
            for i in 0 to 31 put(direct_crypto_mailbox.nonce[i])
            append(iso:"\r\x0aX-Embed-Grant: ")
            append(grant)
            append(iso:"\r\x0aX-Sig: ")
            for i in 0 to 31 {
                put(digits[direct_crypto_mailbox.digest[i]>>4])
                put(digits[direct_crypto_mailbox.digest[i] & 15])
            }
            append(iso:"\r\x0a")
        }
        append(iso:"\r\x0a")
        direct_http_mailbox.request_length=cursor
    }
    sub exchange(ubyte mode,uword maximum) -> bool {
        if direct_radar_mailbox.error!=0 return false
        direct_http_mailbox.mode=mode
        direct_http_mailbox.maximum=maximum
        http_get()
        if direct_http_mailbox.error!=0 or (not direct_http_mailbox.complete and not direct_http_mailbox.prefix_ready) { fail(2)
            return false }
        return true
    }
    sub field(str name) -> bool {
        direct_json_mailbox.scope=scope
        void strings.copy(name,direct_json_mailbox.key)
        json_find()
        if not direct_json_mailbox.found or direct_json_mailbox.error { fail(3)
            return false }
        return true
    }
    sub equals(str value) -> bool {
        ubyte i=0
        while value[i]!=0 {
            if value[i]!=direct_json_mailbox.text[i] return false
            i++
        }
        return i==direct_json_mailbox.length
    }
    sub prefix(str value) -> bool {
        ubyte i=0
        while value[i]!=0 {
            if i>=direct_json_mailbox.length or value[i]!=direct_json_mailbox.text[i] return false
            i++
        }
        return true
    }
    sub integer() -> bool {
        ubyte i
        if direct_json_mailbox.kind!=6 or direct_json_mailbox.length==0 or direct_json_mailbox.length>10 return false
        for i in 0 to direct_json_mailbox.length-1 {
            if direct_json_mailbox.text[i]<48 or direct_json_mailbox.text[i]>57 return false
        }
        return true
    }
    sub observation() {
        epoch_parse()
        if not direct_time_mailbox.valid { fail(3)
            return }
        if direct_time_mailbox.high>direct_radar_mailbox.observed_high or (direct_time_mailbox.high==direct_radar_mailbox.observed_high and direct_time_mailbox.low>direct_radar_mailbox.observed_low) {
            direct_radar_mailbox.observed_low=direct_time_mailbox.low
            direct_radar_mailbox.observed_high=direct_time_mailbox.high
        }
    }
    sub fresh() {
        uword high
        uword age
        utc_date()
        if not direct_time_mailbox.valid or (direct_radar_mailbox.observed_low==0 and direct_radar_mailbox.observed_high==0) { fail(4)
            return }
        if direct_time_mailbox.high<direct_radar_mailbox.observed_high or (direct_time_mailbox.high==direct_radar_mailbox.observed_high and direct_time_mailbox.low<direct_radar_mailbox.observed_low) { fail(4)
            return }
        high=direct_time_mailbox.high-direct_radar_mailbox.observed_high
        if direct_time_mailbox.low<direct_radar_mailbox.observed_low high--
        age=direct_time_mailbox.low-direct_radar_mailbox.observed_low
        if high!=0 or age>1800 or (direct_radar_mailbox.country==0 and age>900) { fail(4)
            return }
        direct_radar_mailbox.age=age
    }
    sub metadata() {
        ubyte i
        ubyte count
        uword root
        uword object
        direct_radar_mailbox.error=0
        direct_radar_mailbox.downloaded=false
        direct_radar_mailbox.observed_low=0
        direct_radar_mailbox.observed_high=0
        json_validate()
        if direct_json_mailbox.error { fail(3)
            return }
        scope=0
        if direct_radar_mailbox.country==0 {
            if not field(iso:"features") or direct_json_mailbox.kind!=3 { fail(3)
                return }
            json_next()
            if direct_json_mailbox.kind!=1 { fail(3)
                return }
            scope=direct_json_mailbox.start
            if not field(iso:"attributes") or direct_json_mailbox.kind!=1 { fail(3)
                return }
            scope=direct_json_mailbox.start
            if not field(iso:"objectid") or not integer() { fail(3)
                return }
            void strings.copy(direct_json_mailbox.text,raster)
            if not field(iso:"idp_validtime") or direct_json_mailbox.kind!=6 or direct_json_mailbox.length!=13 { fail(3)
                return }
            for i in 0 to 12 {
                if direct_json_mailbox.text[i]<48 or direct_json_mailbox.text[i]>57 { fail(3)
                    return }
            }
            direct_json_mailbox.length=10
            direct_json_mailbox.text[10]=0
            observation()
        } else if direct_radar_mailbox.country==1 {
            if not field(iso:"success") or direct_json_mailbox.kind!=7 { fail(3)
                return }
            if not field(iso:"data") or direct_json_mailbox.kind!=1 { fail(3)
                return }
            root=direct_json_mailbox.start
            scope=root
            if not field(iso:"no_data") or direct_json_mailbox.kind!=8 { fail(3)
                return }
            if not field(iso:"tile_version") or not integer() { fail(3)
                return }
            void strings.copy(direct_json_mailbox.text,version)
            if not field(iso:"bounds") or direct_json_mailbox.kind!=3 { fail(3)
                return }
            for i in 0 to 3 {
                json_next()
                if direct_json_mailbox.kind!=6 { fail(3)
                    return }
                when i {
                    0 -> { if not prefix(iso:"115.4154") fail(3) }
                    1 -> { if not prefix(iso:"3.8016") fail(3) }
                    2 -> { if not prefix(iso:"129.5173") fail(3) }
                    3 -> { if not prefix(iso:"22.4585") fail(3) }
                }
                json_next()
                if (i<3 and direct_json_mailbox.kind!=11) or (i==3 and direct_json_mailbox.kind!=4) fail(3)
            }
            if not field(iso:"scale") or direct_json_mailbox.kind!=1 { fail(3)
                return }
            scope=direct_json_mailbox.start
            if not field(iso:"mode") or direct_json_mailbox.kind!=5 or not equals(iso:"rain") fail(3)
            if not field(iso:"unit") or direct_json_mailbox.kind!=5 or not equals(iso:"mm/hr") fail(3)
            if not field(iso:"sqrt") or direct_json_mailbox.kind!=7 fail(3)
            if not field(iso:"max") or direct_json_mailbox.kind!=6 or not equals(iso:"80") fail(3)
            scope=root
            if not field(iso:"timeline") or direct_json_mailbox.kind!=3 { fail(3)
                return }
            json_next()
            count=0
            while direct_json_mailbox.kind==1 and direct_radar_mailbox.error==0 {
                count++
                if count>32 { fail(3)
                    return }
                object=direct_json_mailbox.start
                scope=object
                if not field(iso:"observed_at_unix") or not integer() { fail(3)
                    return }
                observation()
                direct_json_mailbox.position=object
                json_next()
                json_skip()
                json_next()
                if direct_json_mailbox.kind==11 json_next()
            }
            if count==0 or direct_json_mailbox.kind!=4 fail(3)
        } else fail(3)
        if direct_radar_mailbox.error==0 fresh()
    }
    sub meta(str name,uword destination,ubyte capacity) -> ubyte {
        uword index
        uword start
        ubyte size=strings.length(name)
        ubyte i
        bool match
        if direct_http_mailbox.length<=size return 0
        for index in 0 to direct_http_mailbox.length-size {
            match=true
            for i in 0 to size-1 {
                if @(direct_http_mailbox.BODY+index+i)!=name[i] match=false
            }
            if not match continue
            start=index+size
            i=0
            while start<direct_http_mailbox.length {
                ubyte value=@(direct_http_mailbox.BODY+start)
                if value==34 {
                    @(destination+i)=0
                    return i
                }
                if i>=capacity-1 or value<33 or value>126 return 0
                @(destination+i)=value
                i++
                start++
            }
            return 0
        }
        return 0
    }
    sub session() {
        direct_radar_mailbox.error=0
        if meta(iso:"<meta name=\"csrf-token\" content=\"",&csrf,41)!=40 fail(5)
        if meta(iso:"<meta name=\"embed-grant\" content=\"",&grant,96)==0 fail(5)
        direct_crypto_mailbox.key_length=meta(iso:"<meta name=\"api-sig\" content=\"",&direct_crypto_mailbox.key,96)
        if direct_crypto_mailbox.key_length==0 fail(5)
    }
    sub sign() {
        ubyte i
        ubyte value
        utc_date()
        if not direct_time_mailbox.valid { fail(4)
            return }
        epoch_format()
        for i in 0 to 15 {
            value,void,void=cx16.entropy_get()
            direct_crypto_mailbox.nonce[i*2]=digits[value>>4]
            direct_crypto_mailbox.nonce[i*2+1]=digits[value & 15]
        }
        cursor=0
        append(iso:"GET\x0a")
        append(path+1)
        put(10)
        append(direct_crypto_mailbox.timestamp)
        put(10)
        for i in 0 to 31 put(direct_crypto_mailbox.nonce[i])
        direct_crypto_mailbox.pointer=direct_http_mailbox.REQUEST
        direct_crypto_mailbox.length=cursor
        hmac()
        if not direct_crypto_mailbox.valid fail(5)
    }
    sub ph_request() {
        sign()
        begin()
        append(path)
        append(iso:"?token=")
        append(csrf)
    }
    sub download() {
        direct_radar_mailbox.error=0
        direct_radar_mailbox.downloaded=false
        if direct_radar_mailbox.country>1 { fail(1)
            return }
        begin()
        if direct_radar_mailbox.country==0 {
            append(us_service)
            append(iso:"/query?f=json&where=idp_subset%3D%27CONUS%27&outFields=objectid%2Cidp_validtime&returnGeometry=false&orderByFields=idp_validtime%20DESC&resultRecordCount=1")
            headers(false)
            if not exchange(0,8192) return
            metadata()
            if direct_radar_mailbox.error!=0 return
            begin()
            append(us_service)
            append(iso:"/exportImage?f=image&bbox=-2435343.039,2412798.803,2334857.355,5576113.831&bboxSR=")
            direct_radar_projection.append()
            append(iso:"&imageSR=")
            direct_radar_projection.append()
            append(iso:"&size=84,56&format=png32&interpolation=RSP_NearestNeighbor&adjustAspectRatio=false&mosaicRule=%7B%22mosaicMethod%22%3A%22esriMosaicLockRaster%22%2C%22lockRasterIds%22%3A%5B")
            append(raster)
            append(iso:"%5D%7D")
            headers(false)
        } else {
            append(iso:"/?trg=iframe&req=radar.rain-rate")
            headers(false)
            if not exchange(2,1024) return
            session()
            if direct_radar_mailbox.error!=0 return
            path=iso:"/api/v1/radar/timeline"
            ph_request()
            append(iso:"&sublayer=mosaic-rainrate")
            headers(true)
            if not exchange(0,8192) return
            metadata()
            if direct_radar_mailbox.error!=0 return
            path=iso:"/api/v1/radar-data-image"
            ph_request()
            append(iso:"&t=")
            direct_time_mailbox.low=direct_radar_mailbox.observed_low
            direct_time_mailbox.high=direct_radar_mailbox.observed_high
            ; Preserve the signing timestamp while formatting observation time.
            ubyte[12] saved_time
            ubyte i
            for i in 0 to 11 saved_time[i]=direct_crypto_mailbox.timestamp[i]
            epoch_format()
            append(direct_crypto_mailbox.timestamp)
            for i in 0 to 11 direct_crypto_mailbox.timestamp[i]=saved_time[i]
            append(iso:"&mode=rain&size=1024&v=")
            append(version)
            headers(true)
        }
        if not exchange(1,65535) return
        fresh()
        direct_radar_mailbox.downloaded=direct_radar_mailbox.error==0
    }
}
