%import diskio
%import direct_radar_mailbox
%import direct_render_mailbox
%import direct_png_mailbox
%import direct_inflate_mailbox
%import direct_radar_sampling

; Phase overlay in bank 23. The resident app can replace it with the city
; geocoder between operations. Bank 26 changes from inflate history to the PH
; basemap only AFTER the PNG stream and checksums have been verified.
direct_render {
    extsub @bank 3 $a003 = png_open()
    extsub @bank 3 $a006 = png_next()
    extsub @bank 3 $a00c = png_close()
    extsub @bank 3 $a00f = png_pixel()
    const uword GRID=$a600
    ubyte grid_row
    uword started
    ubyte[7] colors=[4,8,5,13,12,11,15]
    ubyte[7] thresholds=[21,64,75,111,157,202,255]
    ubyte[64] tile
    ubyte[16] counts
    ubyte[12] month_days=[31,28,31,30,31,30,31,31,30,31,30,31]
    ubyte tile_count

    sub fail() {
        direct_render_mailbox.phase=4
        direct_radar_mailbox.downloaded=false
        png_close()
    }
    sub read_grid(ubyte x,ubyte y) -> ubyte {
        cx16.r0=GRID+(y as uword)*84+x
        return cx16.fetch(2,25,0)
    }
    sub intensity() -> ubyte {
        ubyte r=direct_png_mailbox.red
        ubyte g=direct_png_mailbox.green
        ubyte b=direct_png_mailbox.blue
        ubyte low=min(r,min(g,b))
        ubyte high=max(r,max(g,b))
        ubyte delta=high-low
        uword hue
        if direct_png_mailbox.alpha<128 return 0
        if low>240 return 7
        if delta<20 or high<39 return 0
        if high==r {
            if g>=b hue=((g-b) as uword)*256/delta
            else hue=1536-((b-g) as uword)*256/delta
        } else if high==g {
            if b>=r hue=512+((b-r) as uword)*256/delta
            else hue=512-((r-b) as uword)*256/delta
        } else {
            if r>=g hue=1024+((r-g) as uword)*256/delta
            else hue=1024-((g-r) as uword)*256/delta
        }
        if hue>1105 return 6
        if hue<85 return 5
        if hue<185 return 4
        if hue<308 return 3
        if hue<692 return 2
        return 1
    }
    sub begin() {
        uword i
        started=cbm.RDTIM16()
        direct_render_mailbox.phase=0
        direct_render_mailbox.step=1
        if not direct_radar_mailbox.downloaded or direct_radar_mailbox.country>1 { fail()
            return }
        png_open()
        if direct_inflate_mailbox.error!=0 { fail()
            return }
        if direct_radar_mailbox.country==0 {
            if direct_png_mailbox.width!=84 or direct_png_mailbox.height!=56 { fail()
                return }
        } else if direct_png_mailbox.width!=750 or direct_png_mailbox.height!=1024 or direct_png_mailbox.color!=4 { fail()
            return }
        for i in 0 to 4703 {
            cx16.r0=GRID+i
            cx16.stavec=2
            cx16.stash(0,25,0)
        }
        grid_row=0
        direct_render_mailbox.phase=1
    }
    sub next() {
        ubyte x
        ubyte level
        ubyte i
        if direct_render_mailbox.phase!=1 return
        ; Check between bounded rows before the 16-bit jiffy clock can wrap.
        ; The resident UI remains free to handle input/cancel between calls.
        if cbm.RDTIM16()-started>36000 { fail()
            return }
        png_next()
        if direct_inflate_mailbox.error!=0 { fail()
            return }
        if direct_png_mailbox.complete {
            if grid_row!=56 { fail()
                return }
            direct_render_mailbox.phase=2
            return
        }
        if not direct_png_mailbox.ready or grid_row>=56 return
        if direct_radar_mailbox.country==1 and direct_png_mailbox.row-1!=direct_radar_sampling.y[grid_row] return
        for x in 0 to 83 {
            level=0
            if direct_radar_mailbox.country==0 {
                direct_png_mailbox.pixel=x
                png_pixel()
                level=intensity()
            } else {
                direct_png_mailbox.pixel=direct_radar_sampling.x[x]
                png_pixel()
                if direct_png_mailbox.alpha>=90 {
                    for i in 0 to 6 {
                        if direct_png_mailbox.red>=thresholds[i] level=i+1
                    }
                }
            }
            cx16.r0=GRID+(grid_row as uword)*84+x
            cx16.stavec=2
            cx16.stash(level,25,0)
        }
        grid_row++
    }
    sub basemap() -> bool {
        uword size
        uword i
        uword checksum=0
        uword index
        if not diskio.f_open(iso:"WCPBASE.BIN") return false
        size=diskio.f_read($7000,8193)
        diskio.f_close()
        if @($7000)!=87 or @($7001)!=67 or @($7002)!=80 or @($7003)!=66 or @($7004)==0 or @($7004)>182 or @($7005)!=42 or @($7006)!=28 or @($7007)!=1 return false
        if size!=2368+(@($7004) as uword)*32 return false
        for i in 4 to size-1 {
            if i!=12 and i!=13 checksum+=@($7000+i)
        }
        if lsb(checksum)!=@($700c) or msb(checksum)!=@($700d) return false
        for i in 0 to 1175 {
            index=mkword(@($7011+i*2),@($7010+i*2))
            if index>=@($7004) return false
        }
        for i in 0 to size-1 {
            cx16.r0=$a000+i
            cx16.stavec=2
            cx16.stash(@($7000+i),26,0)
        }
        return true
    }
    sub make_tile(ubyte x,ubyte y) {
        ubyte i
        ubyte q
        ubyte a
        ubyte level
        uword index
        uword source
        if direct_radar_mailbox.country==1 {
            cx16.r0=$a010+(y as uword)*84+(x as uword)*2
            a=cx16.fetch(2,26,0)
            cx16.r0++
            index=mkword(cx16.fetch(2,26,0),a)
            source=$a940+index*32
            for i in 0 to 31 {
                cx16.r0=source+i
                a=cx16.fetch(2,26,0)
                tile[i*2]=a>>4
                tile[i*2+1]=a & 15
            }
        } else for i in 0 to 63 tile[i]=0
        for q in 0 to 3 {
            level=read_grid(x*2+q % 2,y*2+q/2)
            if level==0 continue
            if level>7 { fail()
                return }
            a=(q/2)*32+(q % 2)*4
            for i in 0 to 15 tile[a+(i/4)*8+i % 4]=colors[level-1]
        }
    }
    sub reduce() {
        ubyte x=0
        ubyte y=0
        ubyte dx
        ubyte dy
        ubyte i
        ubyte color
        ubyte dominant
        ubyte rain
        while y<8 {
            x=0
            while x<8 {
                for i in 0 to 15 counts[i]=0
                for dy in 0 to direct_render_mailbox.step-1 {
                    for dx in 0 to direct_render_mailbox.step-1 {
                        color=tile[(y+dy)*8+x+dx]
                        counts[color]++
                    }
                }
                dominant=0
                for i in 1 to 15 {
                    if counts[i]>counts[dominant] dominant=i
                }
                ; Prioritize actual rain within the same sample cell.
                rain=0
                for i in 0 to 6 {
                    if counts[colors[i]]!=0 rain=colors[i]
                }
                if rain!=0 dominant=rain
                for dy in 0 to direct_render_mailbox.step-1 {
                    for dx in 0 to direct_render_mailbox.step-1 tile[(y+dy)*8+x+dx]=dominant
                }
                x+=direct_render_mailbox.step
            }
            y+=direct_render_mailbox.step
        }
    }
    sub lookup() -> ubyte {
        ubyte index
        ubyte i
        uword address
        bool equal
        for index in 0 to tile_count-1 {
            address=$7010+(index as uword)*32
            equal=true
            for i in 0 to 31 {
                if @(address+i)!=tile[i*2]*16+tile[i*2+1] { equal=false
                    break }
            }
            if equal return index
        }
        if tile_count==207 return 255
        address=$7010+(tile_count as uword)*32
        for i in 0 to 31 @(address+i)=tile[i*2]*16+tile[i*2+1]
        tile_count++
        return tile_count-1
    }
    sub stamp() {
        uword ym
        uword dh
        uword ms
        uword jw
        uword minutes
        uword now
        uword year
        ym,dh,ms,jw=cx16.clock_get_date_time()
        @($7006)=lsb(ym)
        @($7007)=msb(ym)
        @($7008)=lsb(dh)
        if msb(ym)<1 or msb(ym)>12 or lsb(dh)<1 or lsb(dh)>31 or msb(dh)>23 or lsb(ms)>59 or msb(ms)>59 { fail()
            return }
        minutes=0
        if direct_radar_mailbox.age>=msb(ms) minutes=(direct_radar_mailbox.age-msb(ms)+59)/60
        now=(msb(dh) as uword)*60+lsb(ms)
        if now<minutes {
            now+=1440
            if @($7008)>1 @($7008)--
            else {
                if @($7007)>1 @($7007)--
                else { @($7007)=12
                    @($7006)-- }
                @($7008)=month_days[@($7007)-1]
                year=1900+(@($7006) as uword)
                if @($7007)==2 and year % 4==0 and (year % 100!=0 or year % 400==0) @($7008)=29
            }
        }
        now-=minutes
        @($7009)=(now/60) as ubyte
        @($700a)=(now % 60) as ubyte
    }
    sub pack() {
        uword i
        uword checksum
        uword age
        ubyte x
        ubyte y
        ubyte index
        bool overflow
        if direct_render_mailbox.phase!=2 return
        if direct_radar_mailbox.country==1 and not basemap() { fail()
            return }
        direct_render_mailbox.step=1
        repeat {
            for i in 0 to 8991 @($7000+i)=0
            for index in 1 to 7 {
                for i in 0 to 31 @($7010+(index as uword)*32+i)=colors[index-1]*17
            }
            tile_count=8
            overflow=false
            for y in 0 to 27 {
                for x in 0 to 41 {
                    make_tile(x,y)
                    if direct_render_mailbox.phase==4 return
                    if direct_render_mailbox.step>1 reduce()
                    index=lookup()
                    if index==255 { overflow=true
                        break }
                    @($89f0+(y as uword)*84+(x as uword)*2)=index+1
                    @($89f1+(y as uword)*84+(x as uword)*2)=$f1
                }
                if overflow break
            }
            if not overflow break
            if direct_render_mailbox.step==8 { fail()
                return }
            direct_render_mailbox.step*=2
        }
        age=cbm.RDTIM16()-started
        age=age/60+direct_radar_mailbox.age
        if age>1800 or (direct_radar_mailbox.country==0 and age>900) { fail()
            return }
        direct_radar_mailbox.age=age
        @($7000)=87
        @($7001)=67
        @($7002)=82
        @($7003)=52
        @($7004)=tile_count
        @($7005)=direct_radar_mailbox.country
        stamp()
        if direct_render_mailbox.phase==4 return
        checksum=0
        for i in 4 to 11 checksum+=@($7000+i)
        for i in 14 to 8991 checksum+=@($7000+i)
        @($700c)=lsb(checksum)
        @($700d)=msb(checksum)
        direct_render_mailbox.phase=3
    }
    sub cancel() {
        png_close()
        direct_render_mailbox.phase=0
        direct_radar_mailbox.downloaded=false
    }
}
