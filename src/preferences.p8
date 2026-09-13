%import diskio
%import state
%import direct_locations
preferences {
    ubyte[145] data
    sub coordinate(ubyte start,uword limit) -> bool {
        ubyte i
        ubyte ch
        ubyte digits=0
        uword whole=0
        bool fraction=false
        bool nonzero=false
        if data[start+11]!=0 return false
        for i in 0 to 10 {
            ch=data[start+i]
            if ch==0 break
            if ch==45 and i==0 continue
            if ch==46 and not fraction and digits>0 {
                fraction=true
                digits=0
                continue }
            if ch<48 or ch>57 return false
            digits++
            if fraction { if ch!=48 nonzero=true }
            else { whole=whole*10+ch-48
                if whole>limit return false }
        }
        return digits>0 and (whole<limit or not nonzero)
    }
    sub location(ubyte start) -> bool {
        ubyte i
        if not coordinate(start,90) or not coordinate(start+12,180) return false
        if data[start+24]==0 or data[start+39]!=0 return false
        for i in 24 to 38 {
            if data[start+i]!=0 and (data[start+i]<32 or data[start+i]>126) return false
        }
        return true
    }
    sub load() {
        ubyte i
        uword size
        uword checksum=0
        if not diskio.f_open(iso:"WCSETUP.BIN") return
        size=diskio.f_read(data,145)
        diskio.f_close()
        if data[0]!=87 or data[1]!=83 return
        if data[3]>1 or data[5]>1 or data[6]>2 or data[7]>9 return
        if data[4]!=30 and data[4]!=60 and data[4]!=120 return
        if size==100 and data[2]==3 {
            if data[6]==1 or data[8]>1 or data[96]>1 or data[97]>1 return
            for i in 0 to 97 checksum+=data[i]
            if checksum!=mkword(data[99],data[98]) return
            if data[96]!=0 { if not location(16) return }
            if data[97]!=0 { if not location(56) return }
            for i in 0 to 81 @($9890+i)=data[16+i]
            state.country=data[8]
            state.country_choice=state.country
        } else if size!=144 or data[2]!=2 return
        state.units=data[3]
        state.interval=data[4]
        state.automatic=data[5]!=0
        state.source=data[6]
        if state.source==1 state.source=0
        state.home=data[7]
        state.city=state.home
    }
    sub save() {
        ubyte i
        uword checksum=0
        for i in 0 to 144 data[i]=0
        data[0]=87
        data[1]=83
        data[2]=3
        data[3]=state.units
        data[4]=state.interval
        data[5]=state.automatic as ubyte
        data[6]=state.source
        data[7]=state.home
        data[8]=state.country
        for i in 0 to 81 data[16+i]=@($9890+i)
        for i in 0 to 97 checksum+=data[i]
        data[98]=lsb(checksum)
        data[99]=msb(checksum)
        state.saved=false
        if not diskio.f_open_w(iso:"@:WCSETUP.BIN") return
        state.saved=diskio.f_write(data,100)
        diskio.f_close_w()
    }
}
