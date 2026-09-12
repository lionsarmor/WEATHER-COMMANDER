%import direct_json
%import direct_weather_mailbox
%import strings

direct_weather_decode {
    uword current_scope
    uword daily_scope
    uword hourly_scope
    uword row
    uword daily_row
    uword hourly_row
    uword scope
    word value
    uword whole
    uword remainder
    ubyte fraction
    bool negative
    ubyte current_hour
    ubyte day
    ubyte night_code
    byte night_low
    bool night_found
    ubyte[12] month_offsets=[0,3,2,5,0,3,5,1,4,6,2,4]
    ubyte[12] month_days=[31,28,31,30,31,30,31,31,30,31,30,31]

    sub unit(str name,str expected) {
        ubyte i=0
        if not field(name) return
        if direct_json_mailbox.kind!=5 { direct_json_mailbox.error=true
            return }
        while expected[i]!=0 {
            if expected[i]!=direct_json_mailbox.text[i] direct_json_mailbox.error=true
            i++
        }
        if i!=direct_json_mailbox.length direct_json_mailbox.error=true
    }
    sub units() {
        scope=0
        if not field(iso:"current_units") or direct_json_mailbox.kind!=1 { direct_json_mailbox.error=true
            return }
        scope=direct_json_mailbox.start
        unit(iso:"time",iso:"iso8601")
        unit(iso:"temperature_2m",iso:"?F")
        unit(iso:"apparent_temperature",iso:"?F")
        unit(iso:"dew_point_2m",iso:"?F")
        unit(iso:"wind_speed_10m",iso:"mp/h")
        unit(iso:"visibility",iso:"m")
        unit(iso:"pressure_msl",iso:"hPa")
        scope=0
        if not field(iso:"daily_units") or direct_json_mailbox.kind!=1 { direct_json_mailbox.error=true
            return }
        scope=direct_json_mailbox.start
        unit(iso:"temperature_2m_max",iso:"?F")
        unit(iso:"temperature_2m_min",iso:"?F")
        scope=0
        if not field(iso:"hourly_units") or direct_json_mailbox.kind!=1 { direct_json_mailbox.error=true
            return }
        scope=direct_json_mailbox.start
        unit(iso:"temperature_2m",iso:"?F")
        unit(iso:"time",iso:"iso8601")
    }

    sub field(str name) -> bool {
        void strings.copy(name,direct_json_mailbox.key)
        direct_json_mailbox.scope=scope
        direct_json.find()
        if not direct_json_mailbox.found direct_json_mailbox.error=true
        return not direct_json_mailbox.error
    }
    sub decimal(uword divisor) {
        ubyte i=0
        ubyte ch
        uword part
        whole=0
        remainder=0
        fraction=0
        negative=false
        if direct_json_mailbox.kind!=6 { direct_json_mailbox.error=true
            return }
        if direct_json_mailbox.text[0]==45 { negative=true
            i++ }
        while i<direct_json_mailbox.length {
            ch=direct_json_mailbox.text[i]
            if ch==46 {
                i++
                fraction=direct_json_mailbox.text[i]-48
                while i<direct_json_mailbox.length {
                    if not direct_json.digit(direct_json_mailbox.text[i]) direct_json_mailbox.error=true
                    i++
                }
                break
            }
            if not direct_json.digit(ch) or whole>3276 { direct_json_mailbox.error=true
                return }
            part=remainder*10+ch-48
            whole=whole*10+part/divisor
            remainder=part % divisor
            i++
        }
        if divisor==1 {
            if whole>3276 { direct_json_mailbox.error=true
                return }
            value=(whole*10+fraction) as word
            if negative value=-value
        }
    }
    sub rounded() -> word {
        if value<0 return -((-value+5)/10)
        return (value+5)/10
    }
    sub read(str name) -> word {
        if not field(name) return 0
        decimal(1)
        return rounded()
    }
    sub temperature() -> ubyte {
        word number=rounded()
        if number < -128 or number>127 direct_json_mailbox.error=true
        return number as ubyte
    }
    sub code(ubyte wmo, bool daylight) -> ubyte {
        when wmo {
            0 -> { if daylight return 1
                   return 0 }
            1,2,3 -> return 2
            45,48 -> return 6
            71,73,75,77,85,86 -> return 4
            95,96,99 -> return 5
            51,53,55,56,57,61,63,65,66,67,80,81,82 -> return 3
        }
        direct_json_mailbox.error=true
        return 0
    }
    sub pair(ubyte offset) -> ubyte {
        ubyte a=direct_json_mailbox.text[offset]
        ubyte b=direct_json_mailbox.text[offset+1]
        if not direct_json.digit(a) or not direct_json.digit(b) direct_json_mailbox.error=true
        return (a-48)*10+b-48
    }
    sub time() {
        ubyte hour
        ubyte minute
        if direct_json_mailbox.kind!=5 or direct_json_mailbox.length<16 { direct_json_mailbox.error=true
            return }
        if direct_json_mailbox.text[4]!=45 or direct_json_mailbox.text[7]!=45 or direct_json_mailbox.text[10]!=84 or direct_json_mailbox.text[13]!=58 direct_json_mailbox.error=true
        hour=pair(11)
        minute=pair(14)
        if hour>23 or minute>59 direct_json_mailbox.error=true
        whole=hour
        remainder=minute
    }
    sub start_array(str name) {
        if not field(name) return
        if direct_json_mailbox.kind!=3 { direct_json_mailbox.error=true
            return }
        direct_json.next()
    }
    sub advance(ubyte index, ubyte count) {
        direct_json.next()
        if index+1==count {
            if direct_json_mailbox.kind!=4 direct_json_mailbox.error=true
        } else {
            if direct_json_mailbox.kind!=11 direct_json_mailbox.error=true
            direct_json.next()
        }
    }
    sub is_night(ubyte hour) -> bool {
        if current_hour<8 return current_hour+hour<=8
        return current_hour+hour>=18 and current_hour+hour<=32
    }
    sub decode() {
        ubyte i
        ubyte column
        ubyte wmo
        ubyte month
        ubyte date
        uword year
        uword pressure
        uword full_year
        ubyte days
        word number
        direct_weather_mailbox.valid=false
        if direct_weather_mailbox.city>9 return
        direct_json.validate()
        if direct_json_mailbox.error return
        units()
        if direct_json_mailbox.error return
        scope=0
        if not field(iso:"current") or direct_json_mailbox.kind!=1 return
        current_scope=direct_json_mailbox.start
        if not field(iso:"daily") or direct_json_mailbox.kind!=1 return
        daily_scope=direct_json_mailbox.start
        if not field(iso:"hourly") or direct_json_mailbox.kind!=1 return
        hourly_scope=direct_json_mailbox.start
        row=$6420+(direct_weather_mailbox.city as uword)*32
        daily_row=$6560+(direct_weather_mailbox.city as uword)*28
        hourly_row=$6678+(direct_weather_mailbox.city as uword)*24
        for i in 0 to 31 @(row+i)=0
        scope=current_scope
        number=read(iso:"temperature_2m")
        @(row)=temperature()
        number=read(iso:"relative_humidity_2m")
        if number<0 or number>100 direct_json_mailbox.error=true
        @(row+2)=number as ubyte
        number=read(iso:"wind_speed_10m")
        if number<0 or number>200 direct_json_mailbox.error=true
        @(row+3)=number as ubyte
        number=read(iso:"apparent_temperature")
        @(row+8)=temperature()
        number=read(iso:"dew_point_2m")
        @(row+9)=temperature()
        number=read(iso:"is_day")
        if number<0 or number>1 direct_json_mailbox.error=true
        day=number as ubyte
        @(row+13)=day
        number=read(iso:"weather_code")
        if number<0 or number>99 direct_json_mailbox.error=true
        @(row+1)=code(number as ubyte,day!=0)
        number=read(iso:"wind_direction_10m")
        if number<0 or number>360 direct_json_mailbox.error=true
        @(row+12)=(((number as uword)*10+112)/225 % 16) as ubyte
        number=read(iso:"pressure_msl")
        if value<6800 or value>11850 direct_json_mailbox.error=true
        pressure=((value as uword)*3-(value as uword)/20+(value as uword)/333+5)/10
        @(row+16)=lsb(pressure)
        @(row+17)=msb(pressure)
        if pressure<2900 @(row+6)=0
        else if pressure>3100 @(row+6)=200
        else @(row+6)=(pressure-2900) as ubyte
        if not field(iso:"visibility") return
        decimal(1609)
        if negative direct_json_mailbox.error=true
        if remainder>=805 whole++
        if whole>100 whole=100
        @(row+7)=whole as ubyte
        if not field(iso:"time") return
        time()
        current_hour=whole as ubyte
        @(row+22)=current_hour
        @(row+23)=remainder as ubyte
        year=(pair(0) as uword)*100+pair(2)
        month=pair(5)
        date=pair(8)
        if year<1900 or year>2099 or month<1 or month>12 or date<1 or date>31 return
        days=month_days[month-1]
        if month==2 and year % 4==0 and (year % 100!=0 or year % 400==0) days++
        if date>days return
        full_year=year
        if month<3 year--
        @(row+27)=((year+year/4-year/100+year/400+month_offsets[month-1]+date+6) % 7) as ubyte
        @(row+28)=date
        @(row+26)=1
        scope=daily_scope
        for column in 0 to 3 {
            when column {
                0 -> start_array(iso:"temperature_2m_max")
                1 -> start_array(iso:"temperature_2m_min")
                2 -> start_array(iso:"weather_code")
                3 -> start_array(iso:"precipitation_probability_max")
            }
            for i in 0 to 6 {
                decimal(1)
                number=rounded()
                if column<2 @(daily_row+i*4+column)=temperature()
                else if column==2 {
                    if number<0 or number>99 direct_json_mailbox.error=true
                    @(daily_row+i*4+2)=code(number as ubyte,true)
                } else {
                    if number<0 or number>100 direct_json_mailbox.error=true
                    @(daily_row+i*4+3)=number as ubyte
                }
                advance(i,7)
            }
        }
        @(row+5)=@(daily_row+4)
        @(row+15)=@(daily_row+6)
        start_array(iso:"sunrise")
        time()
        @(row+18)=whole as ubyte
        @(row+19)=remainder as ubyte
        start_array(iso:"sunset")
        time()
        @(row+20)=whole as ubyte
        @(row+21)=remainder as ubyte
        scope=hourly_scope
        start_array(iso:"time")
        for i in 0 to 24 {
            if i!=0 and (current_hour+i) % 24==0 {
                date++
                if date>days {
                    date=1
                    month++
                    if month==13 { month=1
                        full_year++ }
                }
            }
            time()
            if whole!=(current_hour+i) % 24 or remainder!=0 direct_json_mailbox.error=true
            if pair(5)!=month or pair(8)!=date or (pair(0) as uword)*100+pair(2)!=full_year direct_json_mailbox.error=true
            advance(i,25)
        }
        night_found=false
        night_low=127
        night_code=0
        for column in 0 to 3 {
            when column {
                0 -> start_array(iso:"temperature_2m")
                1 -> start_array(iso:"weather_code")
                2 -> start_array(iso:"precipitation_probability")
                3 -> start_array(iso:"uv_index")
            }
            for i in 0 to 24 {
                decimal(1)
                number=rounded()
                when column {
                    0 -> {
                        wmo=temperature()
                        if i<8 @(hourly_row+i*3)=wmo
                        if is_night(i) {
                            if not night_found or (wmo as byte)<night_low night_low=wmo as byte
                            night_found=true
                        }
                    }
                    1 -> {
                        if number<0 or number>99 direct_json_mailbox.error=true
                        if i<8 @(hourly_row+i*3+1)=code(number as ubyte,true)
                        if is_night(i) and number>(night_code as word) night_code=number as ubyte
                    }
                    2 -> {
                        if number<0 or number>100 direct_json_mailbox.error=true
                        if i<8 @(hourly_row+i*3+2)=number as ubyte
                        if i<12 and number>(@(row+10) as word) @(row+10)=number as ubyte
                    }
                    3 -> {
                        if value<0 or value>250 direct_json_mailbox.error=true
                        if i==0 @(row+11)=value as ubyte
                    }
                }
                advance(i,25)
            }
        }
        @(row+4)=night_low as ubyte
        @(row+14)=code(night_code,false)
        direct_weather_mailbox.valid=night_found and not direct_json_mailbox.error
    }
}
