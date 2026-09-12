%import syslib
%import strings
%import banner_font
banner {
    &ubyte[32] date=$6d20
    &ubyte[32] location=$6d40
    ubyte[64] previous
    const uword pixels=$ae80 ; reserved 4,480-byte bitmap through $bfff
    bool painted=false
    sub line(str value, ubyte y, ubyte color) {
        ubyte i
        ubyte col
        ubyte row
        ubyte bits
        ubyte n=strings.length(value)
        uword x
        uword address
        uword glyph
        if n==0 return
        if n>23 n=23
        x=(280-(n as uword)*12)/2
        for i in 0 to n-1 {
            glyph=((value[i]-32) as uword)*5
            if value[i]<32 or value[i]>95 glyph=0
            for col in 0 to 4 {
                if glyph+col<256 bits=banner_font.columns[(glyph+col) as ubyte]
                else bits=banner_font.more[(glyph+col-256) as ubyte]
                for row in 0 to 6 {
                    if bits&1!=0 {
                        address=((y+row*2)/8 as uword)*1120+(x/8)*32+((y+row*2) % 8)*4+(x % 8)/2
                        @(pixels+address)=color
                        address=((y+row*2+1)/8 as uword)*1120+(x/8)*32+((y+row*2+1) % 8)*4+(x % 8)/2
                        @(pixels+address)=color
                    }
                    bits=bits>>1
                }
                x+=2
            }
            x+=2
        }
    }
    sub draw() {
        uword i
        uword tile=628
        ubyte row
        ubyte col
        bool same=painted
        for i in 0 to 63 {
            if @($6d20+i)!=previous[i as ubyte] same=false
            previous[i as ubyte]=@($6d20+i)
        }
        if same return
        for i in 0 to 4479 @(pixels+i)=$22
        line(date,1,$66)
        line(location,17,$55)
        for i in 0 to 139 {
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=lsb($4e80+i*32)
            cx16.VERA_ADDR_M=msb($4e80+i*32)
            cx16.VERA_ADDR_H=$10
            for col in 0 to 31 cx16.VERA_DATA0=@(pixels+i*32+col)
            %asm {{ plp }}
        }
        for row in 0 to 3 {
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=$58
            cx16.VERA_ADDR_M=$81+row
            cx16.VERA_ADDR_H=$10
            for col in 0 to 34 {
                cx16.VERA_DATA0=lsb(tile)
                cx16.VERA_DATA0=msb(tile)
                tile++
            }
            %asm {{ plp }}
        }
        painted=true
    }
}
