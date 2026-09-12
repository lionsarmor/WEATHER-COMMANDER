%import direct_time_mailbox
%import direct_http_mailbox
%import direct_json_mailbox
%import direct_crypto_mailbox

direct_time {
    str months=iso:"janfebmaraprmayjunjulaugsepoctnovdec"
    ubyte[12] days_in_month=[31,28,31,30,31,30,31,31,30,31,30,31]
    sub leap(uword year) -> bool {
        return year % 4==0 and (year % 100!=0 or year % 400==0)
    }
    sub add(uword low,uword high) {
        bool carry=low>65535-direct_time_mailbox.low
        if high>65535-direct_time_mailbox.high { direct_time_mailbox.valid=false
            return }
        direct_time_mailbox.low+=low
        direct_time_mailbox.high+=high
        if carry {
            if direct_time_mailbox.high==65535 direct_time_mailbox.valid=false
            direct_time_mailbox.high++
        }
    }
    sub multiply(ubyte factor) {
        uword low=direct_time_mailbox.low
        uword high=direct_time_mailbox.high
        direct_time_mailbox.low=0
        direct_time_mailbox.high=0
        while factor!=0 {
            if factor & 1!=0 add(low,high)
            factor>>=1
            if factor!=0 {
                if high & $8000!=0 direct_time_mailbox.valid=false
                high<<=1
                if low & $8000!=0 high|=1
                low<<=1
            }
        }
    }
    sub pair(ubyte index) -> ubyte {
        ubyte a=direct_http_mailbox.date[index]
        ubyte b=direct_http_mailbox.date[index+1]
        if a<48 or a>57 or b<48 or b>57 direct_time_mailbox.valid=false
        return (a-48)*10+b-48
    }
    sub calendar() {
        uword year
        uword days=0
        ubyte month
        ubyte limit
        if direct_time_mailbox.year<1970 or direct_time_mailbox.year>2099 or direct_time_mailbox.month<1 or direct_time_mailbox.month>12 or direct_time_mailbox.hour>23 or direct_time_mailbox.minute>59 or direct_time_mailbox.second>59 { direct_time_mailbox.valid=false
            return }
        limit=days_in_month[direct_time_mailbox.month-1]
        if direct_time_mailbox.month==2 and leap(direct_time_mailbox.year) limit++
        if direct_time_mailbox.day<1 or direct_time_mailbox.day>limit { direct_time_mailbox.valid=false
            return }
        year=1970
        while year<direct_time_mailbox.year {
            days+=365
            if leap(year) days++
            year++
        }
        month=1
        while month<direct_time_mailbox.month {
            days+=days_in_month[month-1]
            if month==2 and leap(direct_time_mailbox.year) days++
            month++
        }
        days+=direct_time_mailbox.day-1
        direct_time_mailbox.low=days
        direct_time_mailbox.high=0
        multiply(24)
        add(direct_time_mailbox.hour,0)
        multiply(60)
        add(direct_time_mailbox.minute,0)
        multiply(60)
        add(direct_time_mailbox.second,0)
    }
    sub date() {
        ubyte month
        ubyte index
        direct_time_mailbox.valid=true
        if direct_http_mailbox.date[3]!=44 or direct_http_mailbox.date[4]!=32 or direct_http_mailbox.date[7]!=32 or direct_http_mailbox.date[11]!=32 or direct_http_mailbox.date[16]!=32 or direct_http_mailbox.date[19]!=58 or direct_http_mailbox.date[22]!=58 or direct_http_mailbox.date[25]!=32 or direct_http_mailbox.date[26]!=103 or direct_http_mailbox.date[27]!=109 or direct_http_mailbox.date[28]!=116 or direct_http_mailbox.date[29]!=0 { direct_time_mailbox.valid=false
            return }
        direct_time_mailbox.year=(pair(12) as uword)*100+pair(14)
        direct_time_mailbox.day=pair(5)
        direct_time_mailbox.hour=pair(17)
        direct_time_mailbox.minute=pair(20)
        direct_time_mailbox.second=pair(23)
        direct_time_mailbox.month=0
        for month in 0 to 11 {
            index=month*3
            if direct_http_mailbox.date[8]==months[index] and direct_http_mailbox.date[9]==months[index+1] and direct_http_mailbox.date[10]==months[index+2] direct_time_mailbox.month=month+1
        }
        if direct_time_mailbox.valid calendar()
    }
    sub parse() {
        ubyte i
        ubyte digit
        direct_time_mailbox.valid=true
        direct_time_mailbox.low=0
        direct_time_mailbox.high=0
        if direct_json_mailbox.kind!=6 or direct_json_mailbox.length==0 or direct_json_mailbox.length>10 { direct_time_mailbox.valid=false
            return }
        for i in 0 to direct_json_mailbox.length-1 {
            digit=direct_json_mailbox.text[i]
            if digit<48 or digit>57 { direct_time_mailbox.valid=false
                return }
            multiply(10)
            add(digit-48,0)
            if not direct_time_mailbox.valid return
        }
    }
    sub format() {
        uword low=direct_time_mailbox.low
        uword high=direct_time_mailbox.high
        uword quotient_low
        uword quotient_high
        ubyte remainder
        ubyte digit
        ubyte index=10
        direct_crypto_mailbox.timestamp[10]=0
        repeat 10 {
            quotient_low=0
            quotient_high=0
            remainder=0
            repeat 32 {
                remainder<<=1
                if high & $8000!=0 remainder++
                high<<=1
                if low & $8000!=0 high|=1
                low<<=1
                quotient_high<<=1
                if quotient_low & $8000!=0 quotient_high|=1
                quotient_low<<=1
                if remainder>=10 { remainder-=10
                    quotient_low|=1 }
            }
            index--
            direct_crypto_mailbox.timestamp[index]=48+remainder
            low=quotient_low
            high=quotient_high
        }
        index=0
        while index<9 and direct_crypto_mailbox.timestamp[index]==48 index++
        digit=0
        while index<=10 {
            direct_crypto_mailbox.timestamp[digit]=direct_crypto_mailbox.timestamp[index]
            digit++
            index++
        }
    }
}
