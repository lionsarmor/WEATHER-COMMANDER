%import syslib
%import direct_inflate_mailbox

; RFC 1950/1951 decoder. All reads, tree sizes, backreferences and output
; lengths are checked. pull() yields after one bounded output buffer, so the
; PNG bank can unfilter a row without a full uncompressed image in memory.
direct_inflate {
    extsub @bank 3 $a009 = input_byte()
    ubyte bits_left
    ubyte bit_buffer
    ubyte mode
    bool final_block
    uword stored
    uword match_left
    uword distance
    uword cursor
    uword history
    uword adler_a
    uword adler_b
    uword[48] counts
    uword[16] offsets
    uword[256] symbols
    uword[96] symbols_tail
    ubyte[256] lengths
    ubyte[64] lengths_tail
    ubyte[19] order=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
    uword[29] length_base=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
    ubyte[29] length_extra=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
    uword[30] distance_base=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
    ubyte[30] distance_extra=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]

    sub fail(ubyte reason) {
        if direct_inflate_mailbox.error==0 direct_inflate_mailbox.error=reason
        direct_inflate_mailbox.complete=false
    }
    sub read() -> ubyte {
        if direct_inflate_mailbox.error!=0 return 0
        input_byte()
        return direct_inflate_mailbox.character
    }
    sub bits(ubyte count) -> uword {
        uword value=0
        uword mask=1
        repeat count {
            if bits_left==0 {
                bit_buffer=read()
                bits_left=8
            }
            if bit_buffer & 1!=0 value|=mask
            bit_buffer>>=1
            bits_left--
            mask<<=1
        }
        return value
    }
    sub get_length(uword index) -> ubyte {
        if index<256 return lengths[index as ubyte]
        return lengths_tail[(index-256) as ubyte]
    }
    sub set_length(uword index, ubyte size) {
        if index<256 lengths[index as ubyte]=size
        else lengths_tail[(index-256) as ubyte]=size
    }
    sub symbol(uword index) -> uword {
        if index<256 return symbols[index as ubyte]
        return symbols_tail[(index-256) as ubyte]
    }
    sub set_symbol(uword index, uword value) {
        if index<256 symbols[index as ubyte]=value
        else symbols_tail[(index-256) as ubyte]=value
    }
    sub tree(ubyte table, uword first, uword size) {
        uword i
        uword left=1
        uword used=0
        uword base=0
        ubyte n
        ubyte offset=table*16
        if table==1 base=288
        else if table==2 base=320
        for n in 0 to 15 counts[offset+n]=0
        for i in 0 to size-1 {
            n=get_length(first+i)
            if n>15 { fail(3)
                return }
            counts[offset+n]++
            if n!=0 used++
        }
        for n in 1 to 15 {
            left<<=1
            if counts[offset+n]>left { fail(3)
                return }
            left-=counts[offset+n]
        }
        ; The literal tree must end every block. A distance tree can be empty
        ; when its block contains literals only. Single-symbol codes use 1 bit.
        if left!=0 and not (used==1 and counts[offset+1]==1) and not (table==1 and used==0) { fail(3)
            return }
        if table==2 and left!=0 { fail(3)
            return }
        offsets[1]=base
        for n in 2 to 15 offsets[n]=offsets[n-1]+counts[offset+n-1]
        for i in 0 to size-1 {
            n=get_length(first+i)
            if n!=0 {
                set_symbol(offsets[n],i)
                offsets[n]++
            }
        }
    }
    sub decode(ubyte table) -> uword {
        uword value=0
        uword first=0
        uword index=0
        uword count
        ubyte n
        ubyte offset=table*16
        if table==1 index=288
        else if table==2 index=320
        for n in 1 to 15 {
            value=value*2+bits(1)
            count=counts[offset+n]
            if value>=first and value-first<count return symbol(index+value-first)
            index+=count
            first=(first+count)*2
        }
        fail(3)
        return 0
    }
    sub fixed() {
        uword i
        for i in 0 to 287 {
            if i<144 set_length(i,8)
            else if i<256 set_length(i,9)
            else if i<280 set_length(i,7)
            else set_length(i,8)
        }
        tree(0,0,288)
        for i in 0 to 31 lengths[i as ubyte]=5
        tree(1,0,32)
    }
    sub dynamic() {
        uword literal_count=bits(5)+257
        uword distance_count=bits(5)+1
        ubyte code_count=bits(4) as ubyte+4
        uword i
        uword value
        uword copies
        uword total=literal_count+distance_count
        ubyte previous=0
        if literal_count>286 { fail(3)
            return }
        for i in 0 to 18 lengths[i as ubyte]=0
        for i in 0 to (code_count as uword)-1 lengths[order[i as ubyte]]=bits(3) as ubyte
        tree(2,0,19)
        if direct_inflate_mailbox.error!=0 return
        i=0
        while i<total {
            value=decode(2)
            if direct_inflate_mailbox.error!=0 return
            if value<16 {
                previous=value as ubyte
                copies=1
            } else if value==16 {
                if i==0 { fail(3)
                    return }
                copies=bits(2)+3
            } else if value==17 {
                previous=0
                copies=bits(3)+3
            } else if value==18 {
                previous=0
                copies=bits(7)+11
            } else { fail(3)
                return }
            if copies>total-i { fail(3)
                return }
            repeat copies {
                set_length(i,previous)
                i++
            }
        }
        if get_length(256)==0 { fail(3)
            return }
        tree(0,0,literal_count)
        tree(1,literal_count,distance_count)
    }
    sub block() {
        ubyte kind
        uword complement
        final_block=bits(1)!=0
        kind=bits(2) as ubyte
        if kind==0 {
            bits_left=0
            stored=bits(16)
            complement=bits(16)
            if stored ^ complement!=$ffff { fail(2)
                return }
            mode=1
        } else if kind==1 { fixed()
            mode=2
        } else if kind==2 { dynamic()
            mode=2
        } else fail(2)
    }
    sub end_block() {
        uword checksum
        if not final_block { mode=0
            return }
        bits_left=0
        checksum=(read() as uword)*256
        checksum+=read()
        if checksum!=adler_b fail(6)
        checksum=(read() as uword)*256
        checksum+=read()
        if checksum!=adler_a fail(6)
        if direct_inflate_mailbox.remaining!=0 or direct_inflate_mailbox.remaining_high!=0 fail(5)
        mode=3
        direct_inflate_mailbox.complete=direct_inflate_mailbox.error==0
    }
    sub emit(ubyte value) {
        ubyte bank
        if direct_inflate_mailbox.remaining==0 {
            if direct_inflate_mailbox.remaining_high==0 { fail(5)
                return }
            direct_inflate_mailbox.remaining_high--
        }
        direct_inflate_mailbox.remaining--
        @(direct_inflate_mailbox.OUTPUT+direct_inflate_mailbox.count)=value
        direct_inflate_mailbox.count++
        bank=26+(cursor>>13) as ubyte
        cx16.r0=$a000+(cursor & $1fff)
        cx16.stavec=2
        cx16.stash(value,bank,0)
        cursor=(cursor+1) & $7fff
        if history<32768 history++
        if (value as uword)>65520-adler_a adler_a-=65521-value
        else adler_a+=value
        if adler_a>65520-adler_b adler_b-=65521-adler_a
        else adler_b+=adler_a
    }
    sub initialize() {
        ubyte cmf
        ubyte flags
        direct_inflate_mailbox.error=0
        direct_inflate_mailbox.complete=false
        direct_inflate_mailbox.count=0
        bits_left=0
        mode=0
        match_left=0
        cursor=0
        history=0
        adler_a=1
        adler_b=0
        cmf=read()
        flags=read()
        if cmf & 15!=8 or cmf>>4>7 or flags & 32!=0 or ((cmf as uword)*256+flags) % 31!=0 fail(2)
    }
    sub pull() {
        uword value
        uword source
        ubyte index
        ubyte character
        direct_inflate_mailbox.count=0
        if direct_inflate_mailbox.requested==0 or direct_inflate_mailbox.requested>1537 { fail(5)
            return }
        while direct_inflate_mailbox.count<direct_inflate_mailbox.requested and direct_inflate_mailbox.error==0 and not direct_inflate_mailbox.complete {
            if match_left!=0 {
                source=(cursor-distance) & $7fff
                cx16.r0=$a000+(source & $1fff)
                character=cx16.fetch(2,26+(source>>13) as ubyte,0)
                emit(character)
                match_left--
            } else if mode==0 block()
            else if mode==1 {
                if stored==0 end_block()
                else { emit(read())
                    stored-- }
            } else if mode==2 {
                value=decode(0)
                if direct_inflate_mailbox.error!=0 return
                if value<256 emit(value as ubyte)
                else if value==256 end_block()
                else if value<=285 {
                    index=(value-257) as ubyte
                    match_left=length_base[index]+bits(length_extra[index])
                    value=decode(1)
                    if value>=30 { fail(4)
                        return }
                    index=value as ubyte
                    distance=distance_base[index]+bits(distance_extra[index])
                    if distance==0 or distance>history { fail(4)
                        return }
                } else { fail(3)
                    return }
            } else { fail(2)
                return }
        }
    }
}
