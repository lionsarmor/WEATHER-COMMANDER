; -----------------------------------------------------------------------------
; Shared Wi-Fi scan mailbox
; -----------------------------------------------------------------------------
;
; The network screen keeps this list in unbanked RAM so scan results survive
; UART work and remain available to the optional picker helper. The main build
; is capped below $6801; this reserved area stays below the X16 I/O window.

network_mailbox {
    &ubyte[33] ssid=$6950
    &ubyte[64] password=$6980
    &ubyte action=$69c0
    &ubyte focus=$69c1
    &ubyte key=$69c2
    &ubyte connection=$69c5  ; 0 unknown, 1 no card, 2 modem, 3 joined
    &ubyte[40] notice=$69d0
    &ubyte[128] url=$6a00
    &uword destination=$6a80
    &uword maximum=$6a82
    &uword received=$6a84
    &bool receiving=$6a86
    &bool complete=$6a87
    ubyte prefix=0
    ubyte nibble=0
    bool half=false
    sub capture_hex(ubyte ch) {
        if not receiving return
        if prefix<4 {
            when prefix {
                0 -> { if ch==87 prefix=1 }
                1 -> { if ch==67 prefix=2
                       else prefix=0 }
                2 -> { if ch==50 prefix=3
                       else prefix=0 }
                3 -> { if ch==58 { prefix=4
                            received=0
                            half=false }
                       else prefix=0 }
            }
            return
        }
        if ch==13 or ch==10 {
            complete=not half and received>0
            receiving=false
            prefix=0
            return
        }
        ubyte digit
        if ch>=48 and ch<=57 digit=ch-48
        else if ch>=65 and ch<=70 digit=ch-55
        else { receiving=false
            prefix=0
            return }
        if not half { nibble=digit*16
            half=true }
        else {
            if received>=maximum { receiving=false
                prefix=0
                return }
            @(destination+received)=nibble|digit
            received++
            half=false
        }
    }
    const ubyte MAX_ACCESS_POINTS = 10
    const ubyte SSID_LENGTH = 33

    &ubyte[165] names_first = $6801
    &ubyte[165] names_second = $68a6
    &ubyte count = $694b
    &ubyte selected = $694c
    &bool accepted = $694d
    &bool picker_loaded = $694e
    &ubyte scroll = $694f

    sub clear() {
        count = 0
        selected = 0
        accepted = false
        scroll = 0
        names_first[0] = 0
        names_second[0] = 0
    }
    sub initialize() {
        ubyte i
        clear()
        for i in 0 to 127 url[i]=0
        for i in 0 to 63 password[i]=0
        for i in 0 to 32 ssid[i]=0
        for i in 0 to 39 notice[i]=0
        action=0
        focus=0
        connection=0
        receiving=false
        complete=false
        received=0
        destination=$6400
        maximum=1024
    }

    sub character(ubyte entry, ubyte index) -> ubyte {
        if entry < 5
            return names_first[entry * SSID_LENGTH + index]
        return names_second[(entry - 5) * SSID_LENGTH + index]
    }

    sub set_character(ubyte entry, ubyte index, ubyte value) {
        if entry < 5
            names_first[entry * SSID_LENGTH + index] = value
        else
            names_second[(entry - 5) * SSID_LENGTH + index] = value
    }
}
