%import network_driver
%import direct_http_mailbox
%import strings
%import state
%import diskio

direct_http {
    ubyte[128] line
    ubyte line_length
    bool line_overflow
    ubyte phase
    bool chunked
    bool sized
    bool closed
    uword remaining
    uword expected
    uword total_headers
    ubyte chunk_end
    ubyte[100] command
    uword buffered
    bool file_open

    sub reset() {
        direct_http_mailbox.length=0
        direct_http_mailbox.status=0
        direct_http_mailbox.complete=false
        direct_http_mailbox.error=0
        phase=0
        line_length=0
        line_overflow=false
        chunked=false
        sized=false
        closed=false
        remaining=0
        expected=0
        total_headers=0
        chunk_end=0
        buffered=0
        direct_http_mailbox.prefix_ready=false
        direct_http_mailbox.date[0]=0
        if direct_http_mailbox.maximum==0 or direct_http_mailbox.mode>2 direct_http_mailbox.error=1
        if direct_http_mailbox.mode!=1 and direct_http_mailbox.maximum>8192 direct_http_mailbox.error=1
    }
    sub fail() {
        direct_http_mailbox.error=1
        direct_http_mailbox.complete=false
        phase=8
    }
    sub starts(str prefix) -> bool {
        ubyte i=0
        while prefix[i]!=0 {
            if i>=line_length or line[i]!=prefix[i] return false
            i++
        }
        return true
    }
    sub number(ubyte base, ubyte start) -> uword {
        uword value=0
        ubyte i=start
        ubyte digit
        bool any=false
        while i<line_length {
            if line[i]==32 and not any { i++
                continue }
            if line[i]==59 and base==16 break
            if line[i]>=48 and line[i]<=57 digit=line[i]-48
            else if base==16 and line[i]>=97 and line[i]<=102 digit=line[i]-87
            else { fail()
                return 0 }
            if digit>=base or value>(65535-digit)/base { fail()
                return 0 }
            value=value*base+digit
            any=true
            i++
        }
        if not any fail()
        return value
    }
    sub finish_line() {
        if phase==0 {
            if not starts(iso:"http/1.") or line_length<12 { fail()
                return }
            if line[8]!=32 or line[9]<48 or line[9]>57 or line[10]<48 or line[10]>57 or line[11]<48 or line[11]>57 { fail()
                return }
            direct_http_mailbox.status=(line[9]-48 as uword)*100+(line[10]-48 as uword)*10+line[11]-48
            if direct_http_mailbox.status!=200 { fail()
                return }
            phase=1
        } else if phase==1 {
            if line_length==0 {
                ; Binary images must have unambiguous framing; a modem result
                ; string can occur inside compressed image bytes.
                if direct_http_mailbox.mode==1 and not chunked and not sized { fail()
                    return }
                if chunked phase=3
                else if sized {
                    remaining=expected
                    phase=2
                    if remaining==0 { direct_http_mailbox.complete=true
                        phase=7 }
                } else phase=2
            } else if starts(iso:"content-length:") {
                if sized { fail()
                    return }
                if direct_http_mailbox.mode!=2 {
                    expected=number(10,15)
                    sized=true
                    if expected>direct_http_mailbox.maximum fail()
                }
            } else if starts(iso:"transfer-encoding:") {
                if line_length!=26 or not starts(iso:"transfer-encoding: chunked") { fail()
                    return }
                chunked=true
            } else if starts(iso:"content-encoding:") {
                if line_length!=26 or not starts(iso:"content-encoding: identity") fail()
            } else if starts(iso:"date: ") and line_length<46 {
                ubyte i
                for i in 6 to line_length-1 direct_http_mailbox.date[i-6]=line[i]
                direct_http_mailbox.date[line_length-6]=0
            }
        } else if phase==3 {
            remaining=number(16,0)
            if direct_http_mailbox.error!=0 return
            if remaining>direct_http_mailbox.maximum-direct_http_mailbox.length and direct_http_mailbox.mode!=2 { fail()
                return }
            if remaining==0 phase=6
            else phase=4
        } else if phase==6 and line_length==0 {
            direct_http_mailbox.complete=true
            phase=7
        }
    }
    sub flush_file() {
        ubyte saved
        if buffered==0 return
        if not file_open { fail()
            return }
        ; Stop incoming UART bytes while KERNAL owns the CPU for an SD write.
        ; Restore the card's automatic RTS/CTS setting after every block.
        saved=network_driver.MCR
        network_driver.MCR=saved & $dd
        if not diskio.f_write(direct_http_mailbox.BODY,buffered) fail()
        network_driver.MCR=saved
        buffered=0
    }
    sub store_byte(ubyte ch) {
        if direct_http_mailbox.length>=direct_http_mailbox.maximum { fail()
            return }
        if direct_http_mailbox.mode==1 {
            @(direct_http_mailbox.BODY+buffered)=ch
            buffered++
            if buffered==512 flush_file()
        } else @(direct_http_mailbox.BODY+direct_http_mailbox.length)=ch
        direct_http_mailbox.length++
        if direct_http_mailbox.mode==2 and direct_http_mailbox.length==direct_http_mailbox.maximum direct_http_mailbox.prefix_ready=true
    }
    sub feed() {
        ubyte ch=direct_http_mailbox.character
        if direct_http_mailbox.prefix_ready return
        if phase==8 return
        if phase==7 {
            ; Normal completion is followed by the modem's NO CARRIER line.
            if ch==10 {
                line[line_length]=0
                if starts(iso:"no carrier") closed=true
                line_length=0
            } else if ch!=13 and line_length<127 {
                if ch>=65 and ch<=90 ch+=32
                line[line_length]=ch
                line_length++
            }
            return
        }
        if phase==2 or phase==4 {
            store_byte(ch)
            if direct_http_mailbox.error!=0 return
            if phase==4 or sized {
                remaining--
                if remaining==0 {
                    if phase==4 { phase=5
                        chunk_end=0 }
                    else { phase=7
                        direct_http_mailbox.complete=true
                        line_length=0 }
                }
            } else {
                ; Close-delimited HTTP/1.0 JSON/CSV has no length header. The
                ; modem reports EOF after its final CR/LF. Payload parsers
                ; still require a complete, valid document before committing.
                if ch==10 {
                    line[line_length]=0
                    if starts(iso:"no carrier") and line_length==10 {
                        if direct_http_mailbox.length<12 { fail()
                            return }
                        direct_http_mailbox.length-=12
                        direct_http_mailbox.complete=true
                        closed=true
                        phase=7
                    }
                    line_length=0
                } else if ch!=13 {
                    if line_length<127 {
                        if ch>=65 and ch<=90 ch+=32
                        line[line_length]=ch
                        line_length++
                    }
                }
            }
            return
        }
        if phase==5 {
            if (chunk_end==0 and ch!=13) or (chunk_end==1 and ch!=10) { fail()
                return }
            chunk_end++
            if chunk_end==2 { phase=3
                line_length=0 }
            return
        }
        total_headers++
        if total_headers>4096 { fail()
            return }
        if ch==10 {
            if line_overflow {
                ; Public session pages may send long Set-Cookie headers. They
                ; are irrelevant to our grant-based API, but framing headers
                ; must never be accepted after truncation.
                if phase!=1 or starts(iso:"content-") or starts(iso:"transfer-") or starts(iso:"date:") { fail()
                    return }
                line_length=0
                line_overflow=false
                return
            }
            line[line_length]=0
            finish_line()
            line_length=0
            line_overflow=false
        } else if ch!=13 {
            if line_length==127 { line_overflow=true
                return }
            if ch>=65 and ch<=90 ch+=32
            line[line_length]=ch
            line_length++
        }
    }
    sub escape() {
        ; Guard times return a stuck TLS stream to modem command mode.
        network_driver.delay_frames(65)
        void network_driver.transmit(43)
        void network_driver.transmit(43)
        void network_driver.transmit(43)
        network_driver.delay_frames(65)
        void network_driver.send_command(iso:"ATH0",120)
    }
    sub get() {
        uword i
        uword frame=0
        ubyte budget
        ubyte p=6
        reset()
        if direct_http_mailbox.error!=0 return
        if direct_http_mailbox.request_length==0 or direct_http_mailbox.request_length>4095 { fail()
            return }
        ; API staging reuses the radar transfer area, never the active weather.
        state.radar_ready=false
        state.radar_demo=false
        void strings.copy(iso:"ATDS\"",command)
        p=5
        for i in 0 to 78 {
            ubyte ch=direct_http_mailbox.host[i as ubyte]
            if ch==0 break
            if not ((ch>=97 and ch<=122) or (ch>=48 and ch<=57) or ch==45 or ch==46) { fail()
                return }
            command[p]=ch
            p++
        }
        if p==5 or i==79 { fail()
            return }
        command[p]=58
        command[p+1]=52
        command[p+2]=52
        command[p+3]=51
        command[p+4]=34
        command[p+5]=0
        file_open=false
        if direct_http_mailbox.mode==1 {
            file_open=diskio.f_open_w(iso:"@:WCRPNG.BIN")
            if not file_open { fail()
                return }
        }
        network_driver.card_present=true
        if not network_driver.send_command(command,900) { fail()
            direct_http_mailbox.error=2
            escape()
            close_file()
            return }
        for i in 0 to direct_http_mailbox.request_length-1 {
            if not network_driver.transmit(@(direct_http_mailbox.REQUEST+i)) { fail()
                escape()
                close_file()
                return }
        }
        while frame<1800 and not closed and not direct_http_mailbox.prefix_ready {
            budget=128
            while network_driver.LSR & 1!=0 and budget>0 {
                direct_http_mailbox.character=network_driver.DATA
                feed()
                budget--
            }
            if direct_http_mailbox.error!=0 or direct_http_mailbox.prefix_ready break
            sys.waitvsync()
            frame++
        }
        if not closed escape()
        if not direct_http_mailbox.complete and not direct_http_mailbox.prefix_ready fail()
        close_file()
    }
    sub close_file() {
        if not file_open return
        if direct_http_mailbox.error==0 and direct_http_mailbox.complete flush_file()
        diskio.f_close_w()
        file_open=false
    }
}
