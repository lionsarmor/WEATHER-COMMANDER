; Native HTTPS exchange. Request bytes and host are prepared by the API bank.
; The ESP32 performs TLS; HTTP framing and payload validation run on the X16.
direct_http_mailbox {
    &uword request_length=$6d70
    &uword length=$6d72
    &uword maximum=$6d74
    &uword status=$6d76
    &bool complete=$6d78
    &ubyte error=$6d79
    &ubyte character=$6d7a
    &ubyte mode=$6d7b             ; 0 RAM document, 1 SD image, 2 HTML prefix
    &bool prefix_ready=$6d7c      ; explicitly not a complete HTTP document
    &ubyte[80] host=$6d80
    &ubyte[40] date=$6ec0         ; HTTP Date, normalized to lowercase ASCII
    ; The request can reuse body scratch: it is sent in full before receiving
    ; the response. NOAA's exact Albers projection needs a long export URL.
    const uword REQUEST=$8000
    const uword BODY=$7000
}
