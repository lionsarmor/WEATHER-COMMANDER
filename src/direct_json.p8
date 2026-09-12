%import direct_json_mailbox
%import direct_http_mailbox

direct_json {
    ubyte[16] stack
    ubyte depth
    ubyte character
    bool truncated
    sub current_byte() -> ubyte {
        if direct_json_mailbox.position>=direct_http_mailbox.length return 0
        return @(direct_http_mailbox.BODY+direct_json_mailbox.position)
    }
    sub take() -> ubyte {
        ubyte value=current_byte()
        if direct_json_mailbox.position>=direct_http_mailbox.length direct_json_mailbox.error=true
        else direct_json_mailbox.position++
        return value
    }
    sub append(ubyte value) {
        if direct_json_mailbox.length<95 {
            direct_json_mailbox.text[direct_json_mailbox.length]=value
            direct_json_mailbox.length++
        } else truncated=true
    }
    sub digit(ubyte value) -> bool { return value>=48 and value<=57 }
    sub hex(ubyte value) -> ubyte {
        if digit(value) return value-48
        if value>=65 and value<=70 return value-55
        if value>=97 and value<=102 return value-87
        direct_json_mailbox.error=true
        return 0
    }
    sub string() {
        ubyte ch
        ubyte count
        uword value
        while not direct_json_mailbox.error {
            ch=take()
            if ch==34 return
            if ch<32 { direct_json_mailbox.error=true
                return }
            if ch==92 {
                ch=take()
                when ch {
                    34,47,92 -> append(ch)
                    98 -> append(8)
                    102 -> append(12)
                    110 -> append(10)
                    114 -> append(13)
                    116 -> append(9)
                    117 -> {
                        value=0
                        repeat 4 { value=value*16+hex(take()) }
                        if value<128 append(value as ubyte)
                        else append(63)
                    }
                    else -> direct_json_mailbox.error=true
                }
            } else if ch>=128 {
                ; Display strings use ASCII. Consume a complete UTF-8 sequence
                ; and represent unsupported glyphs without corrupting the UI.
                if ch>=194 and ch<=223 count=1
                else if ch>=224 and ch<=239 count=2
                else if ch>=240 and ch<=244 count=3
                else { direct_json_mailbox.error=true
                    return }
                repeat count {
                    ch=take()
                    if ch<128 or ch>191 direct_json_mailbox.error=true
                }
                append(63)
            } else append(ch)
        }
    }
    sub literal(str value, ubyte kind) {
        ubyte i=0
        while value[i]!=0 {
            if take()!=value[i] direct_json_mailbox.error=true
            i++
        }
        direct_json_mailbox.kind=kind
    }
    sub numeric() {
        if current_byte()==45 append(take())
        if current_byte()==48 append(take())
        else {
            if not digit(current_byte()) { direct_json_mailbox.error=true
                return }
            while digit(current_byte()) append(take())
        }
        if current_byte()==46 {
            append(take())
            if not digit(current_byte()) direct_json_mailbox.error=true
            while digit(current_byte()) append(take())
        }
        if current_byte()==101 or current_byte()==69 {
            append(take())
            if current_byte()==43 or current_byte()==45 append(take())
            if not digit(current_byte()) direct_json_mailbox.error=true
            while digit(current_byte()) append(take())
        }
        if truncated direct_json_mailbox.error=true
        direct_json_mailbox.kind=6
    }
    sub next() {
        ubyte ch
        direct_json_mailbox.length=0
        direct_json_mailbox.kind=0
        direct_json_mailbox.text[0]=0
        truncated=false
        if direct_json_mailbox.error return
        ch=current_byte()
        while ch==32 or ch==9 or ch==10 or ch==13 {
            direct_json_mailbox.position++
            ch=current_byte()
        }
        direct_json_mailbox.start=direct_json_mailbox.position
        if direct_json_mailbox.position>=direct_http_mailbox.length {
            direct_json_mailbox.kind=12
            return }
        when ch {
            123 -> { direct_json_mailbox.kind=1
                     direct_json_mailbox.position++ }
            125 -> { direct_json_mailbox.kind=2
                     direct_json_mailbox.position++ }
            91 -> { direct_json_mailbox.kind=3
                    direct_json_mailbox.position++ }
            93 -> { direct_json_mailbox.kind=4
                    direct_json_mailbox.position++ }
            34 -> { direct_json_mailbox.kind=5
                    direct_json_mailbox.position++
                    string() }
            58 -> { direct_json_mailbox.kind=10
                    direct_json_mailbox.position++ }
            44 -> { direct_json_mailbox.kind=11
                    direct_json_mailbox.position++ }
            116 -> literal(iso:"true",7)
            102 -> literal(iso:"false",8)
            110 -> literal(iso:"null",9)
            else -> { if ch==45 or digit(ch) numeric()
                      else direct_json_mailbox.error=true }
        }
        direct_json_mailbox.end=direct_json_mailbox.position
        direct_json_mailbox.text[direct_json_mailbox.length]=0
    }
    sub value() {
        ubyte kind=direct_json_mailbox.kind
        if kind==1 or kind==3 {
            if depth==15 { direct_json_mailbox.error=true
                return }
            depth++
            if kind==1 stack[depth]=1
            else stack[depth]=5
        } else if kind<5 or kind>9 direct_json_mailbox.error=true
    }
    sub validate() {
        direct_json_mailbox.error=false
        direct_json_mailbox.position=0
        depth=0
        stack[0]=0
        while not direct_json_mailbox.error {
            next()
            when stack[depth] {
                0 -> { stack[depth]=9
                       value() }
                1,4 -> {
                    if direct_json_mailbox.kind==2 and stack[depth]==1 depth--
                    else if direct_json_mailbox.kind==5 stack[depth]=2
                    else direct_json_mailbox.error=true
                }
                2 -> {
                    if direct_json_mailbox.kind!=10 direct_json_mailbox.error=true
                    else stack[depth]=3
                }
                3 -> { stack[depth]=8
                       value() }
                5,7 -> {
                    if direct_json_mailbox.kind==4 and stack[depth]==5 depth--
                    else { stack[depth]=6
                           value() }
                }
                6 -> {
                    if direct_json_mailbox.kind==4 depth--
                    else if direct_json_mailbox.kind==11 stack[depth]=7
                    else direct_json_mailbox.error=true
                }
                8 -> {
                    if direct_json_mailbox.kind==2 depth--
                    else if direct_json_mailbox.kind==11 stack[depth]=4
                    else direct_json_mailbox.error=true
                }
                9 -> { if direct_json_mailbox.kind!=12 direct_json_mailbox.error=true
                       return }
            }
        }
    }
    sub skip() {
        ubyte nesting=0
        if direct_json_mailbox.kind==1 or direct_json_mailbox.kind==3 nesting=1
        while nesting>0 and not direct_json_mailbox.error {
            next()
            if direct_json_mailbox.kind==1 or direct_json_mailbox.kind==3 nesting++
            if direct_json_mailbox.kind==2 or direct_json_mailbox.kind==4 nesting--
            if direct_json_mailbox.kind==12 direct_json_mailbox.error=true
        }
    }
    sub find() {
        ubyte i
        bool match
        uword start
        direct_json_mailbox.found=false
        if direct_json_mailbox.error return
        direct_json_mailbox.position=direct_json_mailbox.scope
        next()
        if direct_json_mailbox.kind!=1 { direct_json_mailbox.error=true
            return }
        while not direct_json_mailbox.error {
            next()
            if direct_json_mailbox.kind==2 return
            if direct_json_mailbox.kind!=5 { direct_json_mailbox.error=true
                return }
            match=not truncated
            i=0
            while i<48 {
                if direct_json_mailbox.key[i]!=direct_json_mailbox.text[i] match=false
                if direct_json_mailbox.key[i]==0 break
                i++
            }
            if i==48 match=false
            next()
            if direct_json_mailbox.kind!=10 { direct_json_mailbox.error=true
                return }
            next()
            start=direct_json_mailbox.start
            if match {
                direct_json_mailbox.found=true
                return
            }
            skip()
            next()
            if direct_json_mailbox.kind==2 return
            if direct_json_mailbox.kind!=11 { direct_json_mailbox.error=true
                return }
        }
    }
}
