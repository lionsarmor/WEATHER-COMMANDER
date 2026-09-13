%import diskio
%import state
%import network_mailbox
%import direct_radar_mailbox
%import direct_render_mailbox
radar_feed {
    extsub @bank 12 $a009 = network_radar() clobbers(A,X,Y)
    extsub @bank 23 $a003 = render_begin()
    extsub @bank 23 $a006 = render_next()
    extsub @bank 23 $a009 = render_pack()
    extsub @bank 23 $a00c = render_cancel()
    ubyte[16] header
    ubyte[256] map0
    ubyte[256] map1
    ubyte[256] map2
    ubyte[256] map3
    ubyte[256] map4
    ubyte[256] map5
    ubyte[256] map6
    ubyte[256] map7
    ubyte[256] map8
    ubyte[48] map9
    uword[10] maps=[&map0,&map1,&map2,&map3,&map4,&map5,&map6,&map7,&map8,&map9]
    bool cached=false
    bool sample=false
    ubyte country=255
    ubyte mode=255
    bool attempted=false
    uword attempted_at
    sub cache() {
        uword i
        for i in 0 to 15 header[i as ubyte]=@($7000+i)
        for i in 0 to 2351 @(maps[(i/256) as ubyte]+i % 256)=@($89f0+i)
        cached=true
    }
    sub restore() {
        uword i
        state.radar_ready=false
        state.radar_demo=false
        if not cached or country!=state.country or mode!=state.source return
        for i in 0 to 15 @($7000+i)=header[i as ubyte]
        if not sample and not current() return
        for i in 0 to 2351 @($89f0+i)=@(maps[(i/256) as ubyte]+i % 256)
        state.radar_demo=sample
        state.radar_ready=not sample
    }
    sub cancel() {
        render_cancel()
        attempted=false
    }
    sub step() {
        if direct_render_mailbox.phase==1 {
            render_next()
            if direct_render_mailbox.phase==2 {
                render_pack()
                if direct_render_mailbox.phase==3 and valid(8992,false) {
                    sample=false
                    upload()
                    cache()
                }
            }
        }
        restore()
    }
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
        restore()
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
        uword interval=18000
        if state.country==1 interval=36000
        if country!=state.country or mode!=state.source {
            cancel()
            cached=false
            country=state.country
            mode=state.source
        }
        restore()
        if state.radar_demo or direct_render_mailbox.phase==1 return
        if state.source==0 {
            if state.country==0 size=file(iso:"WCRDEMO.BIN")
            else size=file(iso:"WCRDPH.BIN")
            if valid(size,true) {
                sample=true
                upload()
                cache()
            }
        } else {
            if attempted and cbm.RDTIM16()-attempted_at<interval return
            attempted=true
            attempted_at=cbm.RDTIM16()
            network_radar()
            if direct_radar_mailbox.downloaded render_begin()
        }
        restore()
    }
}
