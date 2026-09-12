%import syslib
%import strings
%import state
ui {
    const ubyte BLACK=1
    const ubyte BLUE=2
    const ubyte CYAN=4
    const ubyte YELLOW=5
    const ubyte WHITE=6
    ; Protect each short VERA transaction from ROM mouse/cursor IRQ activity.
    ; Layer 1 maps at $0:C000 / $1:B000; font at $1:0000.
    ; 4bpp glyphs use palette slots for the foreground/background pair.
    ; Slot zero remains the artwork palette. Tile 256 is fully transparent.
    sub attribute(ubyte color) -> ubyte {
        when color {
            $14 -> return $10
            $15 -> return $20
            $16 -> return $30
            $24 -> return $40
            $25 -> return $50
            $26 -> return $60
            $51 -> return $70
            $e1 -> return $80
            $45 -> return $90
            $f0 -> return $f0
        }
        return 1
    }
    sub at(ubyte x, ubyte y) {
        uword address = $c000 + (y as uword)*256 + (x as uword)*2
        if state.text_bank==1 address-= $1000
        cx16.VERA_CTRL = 0
        cx16.VERA_ADDR_L = lsb(address)
        cx16.VERA_ADDR_M = msb(address)
        cx16.VERA_ADDR_H = $10 | state.text_bank
    }
    sub cell(ubyte x, ubyte y, ubyte glyph, ubyte color) {
        if color==0 glyph=0
        color=attribute(color)
        %asm {{ php
            sei }}
        at(x,y)
        cx16.VERA_DATA0 = glyph
        cx16.VERA_DATA0 = color
        %asm {{ plp }}
    }
    sub text(ubyte x, ubyte y, ubyte color, str value) {
        ubyte i=0
        color=attribute(color)
        %asm {{ php
            sei }}
        at(x,y)
        while value[i] != 0 and x+i < 80 {
            cx16.VERA_DATA0 = value[i]
            cx16.VERA_DATA0 = color
            i++
        }
        %asm {{ plp }}
    }
    sub fill(ubyte x, ubyte y, ubyte width, ubyte height, ubyte color) {
        ubyte row
        ubyte col
        ubyte glyph=32
        if color==0 glyph=0
        color=attribute(color)
        for row in 0 to height-1 {
            %asm {{ php
                sei }}
            at(x,y+row)
            for col in 0 to width-1 {
                cx16.VERA_DATA0=glyph
                cx16.VERA_DATA0=color
            }
            %asm {{ plp }}
        }
    }
    sub number(ubyte x, ubyte y, ubyte color, ubyte value) {
        if value >= 100 { cell(x,y,value/100+48,color)
         x++ }
        if value >= 10 { cell(x,y,value/10 % 10+48,color)
         x++ }
        cell(x,y,value % 10+48,color)
    }
    sub temperature(ubyte x, ubyte y, ubyte color, ubyte raw) {
        word value = raw as byte
        if state.units == 1 value = (value-32)*5/9
        if value < 0 { cell(x,y,45,color)
         x++
        value = -value }
        number(x,y,color,value as ubyte)
        if value >= 100 x++
        if value >= 10 x++
        cell(x+1,y,127,color)
    }
    sub bigdigit(ubyte x, ubyte y, ubyte digit) {
        ubyte base=128+digit*6
        ubyte i
        for i in 0 to 5 cell(x+i % 2,y+i/2,base+i,$15)
    }
    sub bigtemp(ubyte x, ubyte y, ubyte raw) {
        word value = raw as byte
        if state.units == 1 value=(value-32)*5/9
        if value < 0 { cell(x,y,45,$15)
        x++
        value=-value }
        if value >= 100 { bigdigit(x,y,1)
        x+=2 }
        if value >= 10 { bigdigit(x,y,((value as uword)/10 % 10) as ubyte)
        x+=2 }
        bigdigit(x,y,((value as uword) % 10) as ubyte)
        cell(x+2,y,127,$15)
    }
    sub icon(ubyte x, ubyte y, ubyte kind) {
        ubyte i
        ubyte color=$16
        uword base=192+(kind as uword)*16
        if kind==1 color=$15
        if kind>=4 {
            if kind>6 kind=6
            base=464+((kind-4) as uword)*16
        }
        for i in 0 to 15 tile(x+i % 4,y+i/4,base+i,color)
    }
    sub tile(ubyte x, ubyte y, uword glyph, ubyte color) {
        color=attribute(color)|msb(glyph)
        %asm {{ php
            sei }}
        at(x,y)
        cx16.VERA_DATA0=lsb(glyph)
        cx16.VERA_DATA0=color
        %asm {{ plp }}
    }
    ; Even-height bars use paired glyphs with four pixels of top padding and
    ; five below. Odd-height bars use the ordinary font in the middle row.
    sub centered(ubyte x, ubyte y, ubyte w, ubyte h, ubyte color, str value) {
        ubyte n=strings.length(value)
        ubyte i
        ubyte half
        ubyte halves=0
        ubyte ch
        uword glyph
        if n>w n=w
        x+=(w-n)/2
        y+=(h-1)/2
        if h&1==0 halves=1
        color=attribute(color)
        for half in 0 to halves {
            %asm {{ php
                sei }}
            at(x,y+half)
            i=0
            while i<n {
                ch=value[i]
                if ch<32 or ch>127 ch=63
                glyph=ch
                if halves==1 glyph=512+((ch-32) as uword)*2+half
                cx16.VERA_DATA0=lsb(glyph)
                cx16.VERA_DATA0=color|msb(glyph)
                i++
            }
            %asm {{ plp }}
        }
    }
    sub button(ubyte x, ubyte y, ubyte w, ubyte h, ubyte color, str title) {
        fill(x,y,w,h,color)
        centered(x,y,w,h,color,title)
    }
    sub card(ubyte x, ubyte y, ubyte w, ubyte h, str title) {
        fill(x,y,w,h,$16)
        button(x,y,w,2,$45,title)
        fill(x,y+h-1,w,1,$24)
    }
    sub table_temperature(ubyte x, ubyte y, ubyte color, ubyte raw) {
        word value=raw as byte
        ubyte[6] label
        ubyte n=0
        if state.units==1 value=(value-32)*5/9
        if value<0 { label[n]=45
            n++
            value=-value }
        if value>=100 { label[n]=((value as uword)/100) as ubyte+48
            n++ }
        if value>=10 { label[n]=((value as uword)/10 % 10) as ubyte+48
            n++ }
        label[n]=((value as uword) % 10) as ubyte+48
        label[n+1]=127
        label[n+2]=0
        centered(x,y,5,2,color,label)
    }
    sub bigpercent(ubyte x, ubyte y, ubyte value) {
        if value>=100 { bigdigit(x,y,1)
            x+=2 }
        if value>=10 { bigdigit(x,y,value/10 % 10)
            x+=2 }
        bigdigit(x,y,value % 10)
        cell(x+2,y+1,37,$15)
    }
    sub bar(ubyte x, ubyte y, ubyte width, ubyte percent) {
        ubyte filled=((percent as uword)*width/100) as ubyte
        fill(x,y,width,1,$14)
        if filled>0 fill(x,y,filled,1,$45)
    }
    sub time(ubyte x, ubyte y, ubyte color, ubyte hour, ubyte minute) {
        cell(x,y,hour/10+48,color)
        cell(x+1,y,hour % 10+48,color)
        cell(x+2,y,58,color)
        cell(x+3,y,minute/10+48,color)
        cell(x+4,y,minute % 10+48,color)
    }
    sub heading(str title) {
        fill(18,9,42,1,$26)
        centered(18,9,42,1,$26,title)
    }
    sub clear_center() { fill(18,11,42,30,0) }
}
