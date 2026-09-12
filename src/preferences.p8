%import diskio
%import state
%import network_mailbox
preferences {
    ubyte[144] data
    sub load() {
        ubyte i
        uword size
        if not diskio.f_open(iso:"WCSETUP.BIN") return
        size=diskio.f_read(data,144)
        diskio.f_close()
        if size!=144 or data[0]!=87 or data[1]!=83 or data[2]!=2 return
        if data[3]>1 or data[5]>1 or data[6]>2 or data[7]>9 return
        if data[4]!=30 and data[4]!=60 and data[4]!=120 return
        if data[143]!=0 return
        for i in 16 to 142 {
            if data[i]!=0 and (data[i]<33 or data[i]>126 or data[i]==34) return
        }
        state.units=data[3]
        state.interval=data[4]
        state.automatic=data[5]!=0
        state.source=data[6]
        state.home=data[7]
        state.city=state.home
        for i in 0 to 127 network_mailbox.url[i]=data[16+i]
    }
    sub save() {
        ubyte i
        for i in 0 to 143 data[i]=0
        data[0]=87
        data[1]=83
        data[2]=2
        data[3]=state.units
        data[4]=state.interval
        data[5]=state.automatic as ubyte
        data[6]=state.source
        data[7]=state.home
        for i in 0 to 127 {
            if network_mailbox.url[i]==0 break
            data[16+i]=network_mailbox.url[i]
        }
        state.saved=false
        if not diskio.f_open_w(iso:"@:WCSETUP.BIN") return
        state.saved=diskio.f_write(data,144)
        diskio.f_close_w()
    }
}
