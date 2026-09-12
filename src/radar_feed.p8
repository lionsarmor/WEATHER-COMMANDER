%import diskio
%import state
%import network_mailbox
radar_feed {
    extsub @bank 12 $a009 = network_radar() clobbers(A,X,Y)
    sub valid(uword size, bool demo) -> bool {
        uword n
        uword checksum=0
        if size!=8992 return false
        if @($7000)!=87 or @($7001)!=67 or @($7002)!=82 or @($7003)!=52 return false
        if @($7004)==0 or @($7004)>207 or @($7005)!=state.country return false
        if @($700b)!=(demo as ubyte) return false
        for n in 4 to 11 checksum+=@($7000+n)
        for n in 14 to 8991 checksum+=@($7000+n)
        if lsb(checksum)!=@($700c) or msb(checksum)!=@($700d) return false
        if @($7007)<1 or @($7007)>12 or @($7008)<1 or @($7008)>31 or @($7009)>23 or @($700a)>59 return false
        for n in 0 to 1175 {
            if @($89f1+n*2)!=$f1 return false
            if @($89f0+n*2)==0 or @($89f0+n*2)>@($7004) return false
        }
        if demo return true
        if @($700e)!=0 return false
        return current()
    }
    sub current() -> bool {
        uword ym
        uword dh
        uword ms
        uword jw
        uword year
        uword age
        uword now_minutes
        uword file_minutes
        ubyte previous_year
        ubyte previous_month
        ubyte previous_day
        ubyte[12] days=[31,28,31,30,31,30,31,31,30,31,30,31]
        ubyte limit=15
        ym,dh,ms,jw=cx16.clock_get_date_time()
        now_minutes=(msb(dh) as uword)*60+lsb(ms)
        file_minutes=(@($7009) as uword)*60+@($700a)
        previous_year=lsb(ym)
        previous_month=msb(ym)
        previous_day=lsb(dh)
        if previous_month<1 or previous_month>12 or previous_day<1 return false
        if now_minutes<file_minutes {
            if previous_day>1 previous_day--
            else {
                if previous_month>1 previous_month--
                else { previous_month=12
                    previous_year-- }
                previous_day=days[previous_month-1]
                year=1900+(previous_year as uword)
                if previous_month==2 and year % 4==0 and (year % 100!=0 or year % 400==0) previous_day=29
            }
            now_minutes+=1440
        }
        if previous_year!=@($7006) or previous_month!=@($7007) or previous_day!=@($7008) return false
        age=now_minutes-file_minutes
        if state.country==1 limit=30
        return age<=limit
    }
    sub age() {
        if state.radar_ready { if not current() state.radar_ready=false }
    }
    sub file(str name) -> uword {
        uword size=0
        if diskio.f_open(name) {
            size=diskio.f_read($7000,8993)
            diskio.f_close()
        }
        return size
    }
    sub upload() {
        uword n
        ubyte col
        for n in 0 to 206 {
            uword target=$2020+n*32
            uword source=$7010+n*32
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=lsb(target)
            cx16.VERA_ADDR_M=msb(target)
            cx16.VERA_ADDR_H=$11
            for col in 0 to 31 cx16.VERA_DATA0=@(source+col)
            %asm {{ plp }}
        }
    }
    sub refresh() {
        uword size
        state.radar_ready=false
        state.radar_demo=false
        if state.source!=0 {
            ; A connected modem gets the current bridge before any old SD file.
            if state.source==2 and network_mailbox.url[0]!=0 {
                network_radar()
                if network_mailbox.complete {
                    if valid(network_mailbox.received,false) { state.radar_ready=true
                        upload()
                        return }
                }
            } else {
                size=file(iso:"WCRLIVE.BIN")
                if valid(size,false) { state.radar_ready=true
                    upload()
                    return }
            }
        }
        if state.country==0 size=file(iso:"WCRDEMO.BIN")
        else size=file(iso:"WCRDPH.BIN")
        if valid(size,true) {
            state.radar_demo=true
            upload()
        }
    }
}
