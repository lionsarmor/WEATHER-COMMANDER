%import state
%import diskio
%import network_mailbox
provider {
    ubyte[80] demo = [
        54,0,48,6,54,72,110,10, 62,2,63,8,55,68,102,10,
        72,1,42,5,61,77,112,10, 58,3,74,12,49,64,98,7,
        77,1,55,7,66,82,107,10, 78,1,70,9,72,84,105,10,
        63,1,30,11,42,70,108,10, 52,3,82,8,47,56,95,5,
        60,2,65,10,51,65,101,10, 68,2,78,6,55,67,109,6
    ]
    extsub @bank 12 $a006 = network_weather() clobbers(A,X,Y)
    sub demo_data() {
        ubyte i
        uword size
        uword filename=iso:"WCDMUS.BIN"
        if state.country==1 filename=iso:"WCDMPH.BIN"
        if state.country_status==3 {
            filename=iso:"WCDMUS.BIN"
            if state.country_choice==1 filename=iso:"WCDMPH.BIN"
        }
        if diskio.f_open(filename) {
            size=diskio.f_read($6400,1025)
            diskio.f_close()
            if commit(size) { state.status=0
                return }
        }
        for i in 0 to 79 state.records[i]=demo[i]
        state.status=0
        state.extended=false
        state.cycles++
    }
    sub commit(uword size) -> bool {
        ubyte i
        uword n
        uword checksum=0
        if size==128 {
            if @($6400)!=87 or @($6401)!=67 or @($6402)!=49 or @($6403)!=54 return false
            if @($6404)!=1 or @($6405)!=10 return false
            for n in 16 to 95 checksum+=@($6400+n)
            if lsb(checksum)!=@($6408) or msb(checksum)!=@($6409) return false
            for i in 0 to 9 {
                n=$6410+(i as uword)*8
                if @(n+1)>3 or @(n+2)>100 or @(n+3)>200 or @(n+6)>200 or @(n+7)>100 return false
            }
            for i in 0 to 79 state.records[i]=@($6410+i)
            state.country=0
            state.extended=false
            state.status=1
        } else {
            if size!=1024 return false
            if @($6400)!=87 or @($6401)!=67 or @($6402)!=87 or @($6403)!=50 return false
            if @($6404)!=2 or @($6405)!=10 return false
            if @($6406)>1 or @($6407)>1 or @($640f)>1 return false
            if state.country_status==3 and @($640f)!=state.country_choice return false
            checksum=@($6406)+(@($6407) as uword)
            for n in 10 to 1023 checksum+=@($6400+n)
            if lsb(checksum)!=@($6408) or msb(checksum)!=@($6409) return false
            if @($640b)<1 or @($640b)>12 or @($640c)<1 or @($640c)>31 or @($640d)>23 or @($640e)>59 return false
            for i in 0 to 9 {
                n=$6420+(i as uword)*32
                if @(n+1)>7 or @(n+2)>100 or @(n+3)>200 or @(n+7)>100 return false
                if @(n+10)>100 or @(n+12)>15 or @(n+14)>7 or @(n+15)>7 return false
                if @(n+18)>23 or @(n+19)>59 or @(n+20)>23 or @(n+21)>59 return false
                if @(n+22)>23 or @(n+23)>59 return false
                if @(n+26)!=1 return false
            }
            for n in 0 to 69 {
                if @($6562+n*4)>7 or @($6563+n*4)>100 return false
            }
            for n in 0 to 79 {
                if @($6679+n*3)>7 or @($667a+n*3)>100 return false
            }
            for n in 872 to 1015 {
                if @($6400+n)!=0 and (@($6400+n)<32 or @($6400+n)>126) return false
            }
            if @($67e7)!=0 or @($67f7)!=0 return false
            for n in 0 to 1023 @($6000+n)=@($6400+n)
            for i in 0 to 79 state.records[i]=@($6020+(i/8 as uword)*32+i % 8)
            state.country=@($600f)
            state.extended=true
            state.status=3
            if @($6006)==0 state.status=2
            check_age()
        }
        state.cycles++
        return true
    }
    sub check_age() {
        uword ym
        uword dh
        uword ms
        uword jw
        uword now_minutes
        uword file_minutes
        if not state.extended or state.source==0 return
        ym,dh,ms,jw=cx16.clock_get_date_time()
        now_minutes=(msb(dh) as uword)*60+lsb(ms)
        file_minutes=(@($600d) as uword)*60+@($600e)
        if lsb(ym)!=@($600a) or msb(ym)!=@($600b) or lsb(dh)!=@($600c) {
            state.status=2
            return
        }
        if now_minutes<file_minutes or now_minutes-file_minutes>20 state.status=2
    }
    sub refresh() {
        if state.source==0 { demo_data()
            return }
        network_weather()
        if network_mailbox.complete and network_mailbox.received==1024 {
            if commit(1024) return
        }
        ; No card on first startup: use the complete, explicitly labeled demo.
        if network_mailbox.connection==1 or not state.extended {
            state.source=0
            demo_data()
            return }
        state.status=2
    }
}
