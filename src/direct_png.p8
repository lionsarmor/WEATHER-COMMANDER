%import syslib
%import diskio
%import direct_png_mailbox
%import direct_inflate_mailbox

; PNG 8-bit, non-interlaced scanline decoder (W3C PNG specification).
; Row storage: current in resident scratch, previous in data bank 25.
; Streaming DEFLATE history: data banks 26..29, owned by bank 24.
direct_png {
    extsub @bank 24 $a003 = inflate_initialize()
    extsub @bank 24 $a006 = inflate_pull()
    ; Keep compressed input in this bank so the resident app may refresh
    ; weather between completed scanlines without corrupting the open image.
    ubyte[256] file_buffer
    uword file_position
    uword file_size
    uword file_total
    bool file_open
    uword chunk_left
    ubyte[4] chunk_type
    uword crc_low
    uword crc_high
    uword palette_size
    ubyte[256] red
    ubyte[256] green
    ubyte[256] blue
    ubyte[256] alpha
    bool transparency
    ubyte transparent_red
    ubyte transparent_green
    ubyte transparent_blue
    bool saw_transparency
    ubyte[8] signature=[137,80,78,71,13,10,26,10]

    sub fail() {
        if direct_inflate_mailbox.error==0 direct_inflate_mailbox.error=7
        direct_png_mailbox.ready=false
        direct_png_mailbox.complete=false
    }
    sub raw() -> ubyte {
        ubyte result
        if direct_inflate_mailbox.error!=0 return 0
        if file_position==file_size {
            file_size=diskio.f_read(file_buffer,256)
            file_position=0
            if file_size==0 { fail()
                return 0 }
        }
        if file_total==$ffff { fail()
            return 0 }
        result=file_buffer[file_position as ubyte]
        file_position++
        file_total++
        return result
    }
    sub crc(ubyte value) {
        bool bit
        crc_low^=value as uword
        repeat 8 {
            bit=crc_low & 1!=0
            crc_low>>=1
            if crc_high & 1!=0 crc_low|=$8000
            crc_high>>=1
            if bit { crc_low^=$8320
                crc_high^=$edb8 }
        }
    }
    sub data() -> ubyte {
        ubyte value
        if chunk_left==0 { fail()
            return 0 }
        value=raw()
        chunk_left--
        crc(value)
        return value
    }
    sub check_crc() {
        uword high
        uword low
        if chunk_left!=0 { fail()
            return }
        high=(raw() as uword)*256
        high+=raw()
        low=(raw() as uword)*256
        low+=raw()
        if high!=(crc_high ^ $ffff) or low!=(crc_low ^ $ffff) fail()
    }
    sub header() {
        ubyte i
        ubyte value
        if raw()!=0 or raw()!=0 { fail()
            return }
        chunk_left=(raw() as uword)*256
        chunk_left+=raw()
        crc_low=$ffff
        crc_high=$ffff
        for i in 0 to 3 {
            value=raw()
            if not ((value>=65 and value<=90) or (value>=97 and value<=122)) fail()
            chunk_type[i]=value
            crc(value)
        }
        if chunk_type[2] & 32!=0 fail()
    }
    sub is_chunk(ubyte a,ubyte b,ubyte c,ubyte d) -> bool {
        return chunk_type[0]==a and chunk_type[1]==b and chunk_type[2]==c and chunk_type[3]==d
    }
    sub skip() {
        while chunk_left!=0 and direct_inflate_mailbox.error==0 void data()
        check_crc()
    }
    sub input_byte() {
        if direct_inflate_mailbox.error!=0 return
        while chunk_left==0 and direct_inflate_mailbox.error==0 {
            check_crc()
            header()
            if not is_chunk(73,68,65,84) { fail()
                return }
        }
        direct_inflate_mailbox.character=data()
    }
    sub close() {
        if file_open diskio.f_close()
        file_open=false
    }
    sub open() {
        ubyte i
        uword index
        uword count
        close()
        direct_inflate_mailbox.error=0
        direct_png_mailbox.ready=false
        direct_png_mailbox.complete=false
        direct_png_mailbox.row=0
        palette_size=0
        transparency=false
        saw_transparency=false
        for i in 0 to 255 alpha[i]=255
        file_position=0
        file_size=0
        file_total=0
        file_open=diskio.f_open(iso:"WCRPNG.BIN")
        if not file_open { fail()
            return }
        for i in 0 to 7 {
            if raw()!=signature[i] { fail()
                close()
                return }
        }
        header()
        if not is_chunk(73,72,68,82) or chunk_left!=13 { fail()
            close()
            return }
        if data()!=0 or data()!=0 fail()
        direct_png_mailbox.width=(data() as uword)*256
        direct_png_mailbox.width+=data()
        if data()!=0 or data()!=0 fail()
        direct_png_mailbox.height=(data() as uword)*256
        direct_png_mailbox.height+=data()
        if data()!=8 fail()
        direct_png_mailbox.color=data()
        when direct_png_mailbox.color {
            0,3 -> direct_png_mailbox.channels=1
            2 -> direct_png_mailbox.channels=3
            4 -> direct_png_mailbox.channels=2
            6 -> direct_png_mailbox.channels=4
            else -> fail()
        }
        if data()!=0 or data()!=0 or data()!=0 fail()
        check_crc()
        if direct_png_mailbox.width<2 or direct_png_mailbox.width>1536 or direct_png_mailbox.height<2 or direct_png_mailbox.height>1024 fail()
        direct_png_mailbox.row_bytes=direct_png_mailbox.width*direct_png_mailbox.channels
        if direct_png_mailbox.row_bytes>1536 fail()
        while direct_inflate_mailbox.error==0 {
            header()
            if is_chunk(73,68,65,84) break
            if is_chunk(80,76,84,69) {
                if palette_size!=0 or chunk_left==0 or chunk_left>768 or chunk_left % 3!=0 or direct_png_mailbox.color==0 or direct_png_mailbox.color==4 { fail()
                    break }
                palette_size=chunk_left/3
                for index in 0 to palette_size-1 {
                    red[index as ubyte]=data()
                    green[index as ubyte]=data()
                    blue[index as ubyte]=data()
                }
                check_crc()
            } else if is_chunk(116,82,78,83) {
                if saw_transparency { fail()
                    break }
                saw_transparency=true
                if direct_png_mailbox.color==3 {
                    if palette_size==0 or chunk_left==0 or chunk_left>palette_size { fail()
                        break }
                    count=chunk_left
                    for index in 0 to count-1 alpha[index as ubyte]=data()
                } else if direct_png_mailbox.color==0 and chunk_left==2 {
                    if data()!=0 fail()
                    transparent_red=data()
                    transparency=true
                } else if direct_png_mailbox.color==2 and chunk_left==6 {
                    if data()!=0 fail()
                    transparent_red=data()
                    if data()!=0 fail()
                    transparent_green=data()
                    if data()!=0 fail()
                    transparent_blue=data()
                    transparency=true
                } else fail()
                check_crc()
            } else if chunk_type[0] & 32!=0 skip()
            else fail()
        }
        if direct_png_mailbox.color==3 and palette_size==0 fail()
        if direct_inflate_mailbox.error!=0 { close()
            return }
        direct_inflate_mailbox.remaining=0
        direct_inflate_mailbox.remaining_high=0
        count=direct_png_mailbox.row_bytes+1
        for index in 0 to direct_png_mailbox.height-1 {
            if direct_inflate_mailbox.remaining>65535-count direct_inflate_mailbox.remaining_high++
            direct_inflate_mailbox.remaining+=count
        }
        inflate_initialize()
        if direct_inflate_mailbox.error!=0 close()
    }
    sub paeth(ubyte a,ubyte b,ubyte c) -> ubyte {
        ; Separate mixed-width operations: Prog8 12.3.2 reuses a scratch
        ; operand in the combined (word + byte - byte) expression.
        word p=a as word
        p+=b
        p-=c
        word pa=p-a
        word pb=p-b
        word pc=p-c
        if pa<0 pa=-pa
        if pb<0 pb=-pb
        if pc<0 pc=-pc
        if pa<=pb and pa<=pc return a
        if pb<=pc return b
        return c
    }
    sub finish() {
        direct_inflate_mailbox.requested=1
        inflate_pull()
        if not direct_inflate_mailbox.complete or direct_inflate_mailbox.count!=0 or chunk_left!=0 fail()
        check_crc()
        while direct_inflate_mailbox.error==0 {
            header()
            if is_chunk(73,69,78,68) {
                if chunk_left!=0 fail()
                check_crc()
                break
            }
            if chunk_type[0] & 32==0 { fail()
                break }
            skip()
        }
        if direct_inflate_mailbox.error==0 {
            if file_position!=file_size or diskio.f_read(file_buffer,1)!=0 fail()
        }
        direct_png_mailbox.complete=direct_inflate_mailbox.error==0
        close()
    }
    sub next_row() {
        uword i
        ubyte filter
        ubyte value
        ubyte left
        ubyte above
        ubyte upper_left
        direct_png_mailbox.ready=false
        if direct_inflate_mailbox.error!=0 { close()
            return }
        if direct_png_mailbox.complete return
        if direct_png_mailbox.row==direct_png_mailbox.height { finish()
            return }
        direct_inflate_mailbox.requested=direct_png_mailbox.row_bytes+1
        inflate_pull()
        if direct_inflate_mailbox.error!=0 or direct_inflate_mailbox.count!=direct_inflate_mailbox.requested { fail()
            close()
            return }
        filter=@($7000)
        if filter>4 { fail()
            close()
            return }
        for i in 0 to direct_png_mailbox.row_bytes-1 {
            value=@($7001+i)
            left=0
            above=0
            upper_left=0
            if i>=direct_png_mailbox.channels left=@($7001+i-direct_png_mailbox.channels)
            if direct_png_mailbox.row!=0 {
                cx16.r0=$a000+i
                above=cx16.fetch(2,25,0)
                ; Previous row remains intact until the whole row is unfiltered.
                if i>=direct_png_mailbox.channels {
                    cx16.r0=$a000+i-direct_png_mailbox.channels
                    upper_left=cx16.fetch(2,25,0)
                }
            }
            when filter {
                1 -> value+=left
                2 -> value+=above
                3 -> value+=(((left as uword)+above)/2) as ubyte
                4 -> value+=paeth(left,above,upper_left)
            }
            if direct_png_mailbox.color==3 and (value as uword)>=palette_size fail()
            @($7001+i)=value
        }
        for i in 0 to direct_png_mailbox.row_bytes-1 {
            cx16.r0=$a000+i
            cx16.stavec=2
            cx16.stash(@($7001+i),25,0)
        }
        direct_png_mailbox.row++
        direct_png_mailbox.ready=direct_inflate_mailbox.error==0
    }
    sub pixel() {
        uword pointer
        ubyte index
        direct_png_mailbox.alpha=0
        if not direct_png_mailbox.ready or direct_png_mailbox.pixel>=direct_png_mailbox.width return
        pointer=$7001+direct_png_mailbox.pixel*direct_png_mailbox.channels
        index=@(pointer)
        direct_png_mailbox.red=index
        direct_png_mailbox.green=index
        direct_png_mailbox.blue=index
        direct_png_mailbox.alpha=255
        when direct_png_mailbox.color {
            0 -> { if transparency and index==transparent_red direct_png_mailbox.alpha=0 }
            2,6 -> {
                direct_png_mailbox.green=@(pointer+1)
                direct_png_mailbox.blue=@(pointer+2)
                if direct_png_mailbox.color==6 direct_png_mailbox.alpha=@(pointer+3)
                else if transparency and index==transparent_red and @(pointer+1)==transparent_green and @(pointer+2)==transparent_blue direct_png_mailbox.alpha=0
            }
            3 -> {
                direct_png_mailbox.red=red[index]
                direct_png_mailbox.green=green[index]
                direct_png_mailbox.blue=blue[index]
                direct_png_mailbox.alpha=alpha[index]
            }
            4 -> direct_png_mailbox.alpha=@(pointer+1)
        }
    }
}
