%import syslib
%import strings
%import network_mailbox

; -----------------------------------------------------------------------------
; TexElec X16 Serial & ESP32 Network Card driver
; -----------------------------------------------------------------------------
;
; The card's first 16450-compatible UART is the ZiModem network port. This
; alpha intentionally supports the factory-default IO7-low address only.

network_driver {
    &ubyte DATA = $9fe0          ; receive buffer / transmit holding / DLL
    &ubyte IER = $9fe1           ; interrupt enable / divisor high
    &ubyte FCR = $9fe2           ; FIFO control
    &ubyte LCR = $9fe3           ; line control
    &ubyte MCR = $9fe4           ; modem control
    &ubyte LSR = $9fe5           ; line status
    &ubyte MSR = $9fe6           ; modem status
    &ubyte SCRATCH = $9fe7       ; safe read/write presence probe

    ; The diagnostic transcript is capped, while ATW10 SSIDs are parsed live
    ; into network_mailbox. This avoids needing a >256-byte Prog8 array.
    const ubyte RESPONSE_SIZE = 255

    ; Keep the transcript after the shared SSID mailbox. main.p8 enforces a
    ; $9800 ceiling, preventing core code from ever overlapping these bytes.
    &ubyte[256] response = $6c00
    &ubyte response_length = $6d00
    bool capture_networks
    ubyte[33] scan_name
    ubyte scan_name_length
    ubyte scan_previous
    bool scan_name_done
    bool card_present
    bool modem_present
    ubyte[8] result_line
    ubyte result_line_length
    bool result_seen
    bool result_ok

    sub detect_card() -> bool {
        ubyte saved = SCRATCH

        ; A real 16450 scratch register retains both patterns. Empty expansion
        ; space does not. Restore the original byte before returning.
        SCRATCH = $55
        if SCRATCH != $55 {
            SCRATCH = saved
            card_present = false
            return false
        }
        SCRATCH = $aa
        if SCRATCH != $aa {
            SCRATCH = saved
            card_present = false
            return false
        }
        SCRATCH = saved
        card_present = true
        initialize_uart()
        return true
    }

    sub initialize_uart() {
        ; 14.7456 MHz / 16 gives a 921600 baud base. Divisor 8 is 115200.
        IER = 0
        LCR = $80                ; expose divisor registers
        DATA = 8
        IER = 0
        LCR = $03                ; 8 data bits, no parity, 1 stop bit
        FCR = $87                ; enable/clear FIFOs; receive trigger = 8

        ; DTR + RTS + OUT1 and hardware auto-RTS/CTS. OUT1 is the important
        ; TexElec Option Pin A control. The earlier $23 omitted it, allowing
        ; the UART to probe correctly while leaving ZiModem unable to answer.
        MCR = $27
        flush_receiver()
    }

    sub delay_frames(ubyte frames) {
        while frames > 0 {
            sys.waitvsync()
            frames--
        }
    }

    sub flush_receiver() {
        ubyte discarded
        ; Never let a noisy/stuck UART hold the whole desktop forever. Reading
        ; up to one full byte-page is enough to drain stale command data; any
        ; continuing stream is handled by the timed response loop instead.
        uword remaining = 256
        while LSR & 1 != 0 and remaining > 0 {
            discarded = DATA
            remaining--
        }
    }

    sub transmit(ubyte character) -> bool {
        uword timeout = 0

        ; Bit 5 means the transmit holding register can accept a byte.
        while LSR & $20 == 0 and timeout < 60000
            timeout++
        if timeout == 60000
            return false
        DATA = character
        return true
    }

    sub set_response(str message) {
        ubyte index = 0
        while message[index] != 0 and index < RESPONSE_SIZE - 1 {
            response[index] = message[index]
            index++
        }
        response[index] = 0
        response_length = index
    }

    sub begin_network_capture() {
        network_mailbox.clear()
        capture_networks = true
        scan_name_length = 0
        scan_previous = 0
        scan_name_done = false
    }

    sub end_network_capture() {
        capture_networks = false
    }

    sub capture_network_character(ubyte character) {
        if not capture_networks
            return

        if character == $0d or character == $0a {
            if scan_name_done and scan_name_length > 0 and
               network_mailbox.count < network_mailbox.MAX_ACCESS_POINTS {
                ubyte index
                for index in 0 to scan_name_length - 1
                    network_mailbox.set_character(network_mailbox.count,
                                                  index, scan_name[index])
                network_mailbox.set_character(network_mailbox.count,
                                              scan_name_length, 0)
                network_mailbox.count++
            }
            scan_name_length = 0
            scan_previous = 0
            scan_name_done = false
            return
        }

        ; ZiModem rows end in " (-42)*". Once " (" arrives, the bytes already
        ; collected are the complete SSID and the RSSI suffix can be ignored.
        if not scan_name_done {
            if character == '(' and scan_previous == ' ' {
                if scan_name_length > 0 and
                   scan_name[scan_name_length - 1] == ' '
                    scan_name_length--
                scan_name_done = true
            } else if scan_name_length < 32 {
                scan_name[scan_name_length] = character
                scan_name_length++
            }
        }
        scan_previous = character
    }

    sub track_result(ubyte character) {
        ; ZiModem finishes an AT command with a line containing OK or ERROR.
        ; Track that line separately so a long Wi-Fi list can fill the visible
        ; response buffer without hiding the command's final result.
        if character == $0d or character == $0a {
            ; UART data is ASCII. Prog8 letter character literals use the
            ; X16/PETSCII character value (for example 'O' is $cf), so use
            ; explicit ASCII wire bytes for every modem result comparison.
            if result_line_length == 2 and
               result_line[0] == $4f and result_line[1] == $4b {
                result_seen = true
                result_ok = true
            } else if result_line_length == 1 and
                      result_line[0] == '0' {
                ; ATV0 uses numeric result codes: zero is OK.
                result_seen = true
                result_ok = true
            } else if result_line_length == 5 and
                      result_line[0] == $45 and result_line[1] == $52 and
                      result_line[2] == $52 and result_line[3] == $4f and
                      result_line[4] == $52 {
                result_seen = true
                result_ok = false
            } else if result_line_length == 1 and
                      result_line[0] == '4' {
                ; ATV0 uses four for ERROR.
                result_seen = true
                result_ok = false
            } else if result_line_length >= 7 and
                      (result_line[0] & $5f) == $43 and
                      (result_line[1] & $5f) == $4f and
                      (result_line[2] & $5f) == $4e and
                      (result_line[3] & $5f) == $4e and
                      (result_line[4] & $5f) == $45 and
                      (result_line[5] & $5f) == $43 and
                      (result_line[6] & $5f) == $54 {
                result_seen = true
                result_ok = true
            }
            result_line_length = 0
        } else if result_line_length < 7 {
            result_line[result_line_length] = character
            result_line_length++
        } else
            result_line_length = 8
    }

    sub read_response(uword maximum_frames) {
        uword frame = 0
        ubyte quiet_frames = 0

        response_length = 0
        response[0] = 0
        result_line_length = 0
        result_seen = false
        result_ok = false
        while frame < maximum_frames {
            bool received_this_frame = false
            ; Bound work per video frame. This makes maximum_frames a real
            ; timeout even if the card continuously asserts data-ready.
            ubyte byte_budget = 64
            while LSR & 1 != 0 and byte_budget > 0 {
                ubyte character = DATA
                byte_budget--
                received_this_frame = true
                capture_network_character(character)
                network_mailbox.capture_hex(character)
                track_result(character)
                if response_length < RESPONSE_SIZE - 1 {
                    ; Preserve CR/LF: higher-level clients parse the completed
                    ; response after this routine returns and need real record
                    ; boundaries between chat messages. Replace only other
                    ; non-printing controls in the diagnostic transcript.
                    if character < 32 and character != $0d and character != $0a
                        character = ' '
                    response[response_length] = character
                    response_length++
                    response[response_length] = 0
                }
            }

            if received_this_frame
                quiet_frames = 0
            else
                quiet_frames++

            ; Some physical ZiModem firmware/profile combinations finish the
            ; last result with "OK" but no trailing CR/LF. Once the UART has
            ; been quiet for a few frames, commit that pending line exactly as
            ; if its line ending had arrived. Without this, the UI displayed
            ; OK while send_command() incorrectly returned false.
            if not result_seen and quiet_frames > 3 and
               result_line_length > 0
                track_result($0d)

            ; Do not stop on an echoed command. Wait for ZiModem's complete
            ; result line, then allow a few frames for the final characters.
            if result_seen and quiet_frames > 3
                return

            sys.waitvsync()
            frame++
        }
    }

    sub response_has_ok_line() -> bool {
        ubyte index = 0

        ; Hardware is the authority here: if the diagnostic buffer visibly
        ; contains a complete standalone OK line, accept it even when an odd
        ; startup/line-ending sequence confused the streaming line tracker.
        ; Requiring boundaries prevents an SSID or banner word containing
        ; "OK" from being mistaken for a command result.
        while index + 1 < response_length {
            ; ATC/ATD return CONNECT rather than OK after a real outbound TCP
            ; socket opens. Treat that documented result as command success.
            ; $5f folds ASCII lower-case and ZiModem high-bit/PETSCII letter
            ; forms into the same upper-case value. Physical firmware returned
            ; a visible "CONNECT 2" that the old byte-exact test missed.
            if index + 6 < response_length and
               (response[index] & $5f) == $43 and
               (response[index + 1] & $5f) == $4f and
               (response[index + 2] & $5f) == $4e and
               (response[index + 3] & $5f) == $4e and
               (response[index + 4] & $5f) == $45 and
               (response[index + 5] & $5f) == $43 and
               (response[index + 6] & $5f) == $54
                return true
            if response[index] == $4f and response[index + 1] == $4b {
                bool left_boundary = index == 0 or response[index - 1] <= 32
                bool right_boundary = index + 2 == response_length or
                                      response[index + 2] <= 32
                if left_boundary and right_boundary
                    return true
            }
            index++
        }
        return false
    }

    sub send_command(str command, uword wait_frames) -> bool {
        ubyte index = 0

        if not card_present {
            set_response(iso:"CARD NOT DETECTED")
            return false
        }

        flush_receiver()
        while command[index] != 0 {
            if not transmit(command[index]) {
                set_response(iso:"UART SEND TIMEOUT")
                return false
            }
            index++
        }
        ; ZiModem's X16 reference transport terminates every command with both
        ; carriage return and line feed. Sending only CR worked with some saved
        ; profiles but was not dependable on the physical card.
        if not transmit($0d) or not transmit($0a) {
            set_response(iso:"UART SEND TIMEOUT")
            return false
        }
        read_response(wait_frames)
        return (result_seen and result_ok) or response_has_ok_line()
    }

    sub response_contains(str wanted) -> bool {
        ubyte wanted_length = strings.length(wanted)
        ubyte start = 0

        if wanted_length == 0
            return true
        while start + wanted_length <= response_length {
            ubyte offset = 0
            bool matches = true
            while offset < wanted_length {
                if response[start + offset] != wanted[offset]
                    matches = false
                offset++
            }
            if matches
                return true
            start++
        }
        return false
    }

    sub detect_modem() -> bool {
        bool configured

        modem_present = false
        if not detect_card()
            return false

        ; Match the working X16 ZiModem startup sequence. Give the ESP32 time
        ; to settle, abort a leftover AT&G/stream transfer with Ctrl-C, then
        ; force a predictable ASCII command profile before identification.
        delay_frames(10)
        void transmit($03)
        delay_frames(5)
        flush_receiver()

        ; Echo off, responses on, verbose/extended results, RTS/CTS, CR/LF,
        ; raw AT&G payloads, ASCII mode, and hardware flow control. These are
        ; runtime settings only; Desk Commander does not overwrite the user's
        ; saved ZiModem profile during detection.
        configured = send_command(
            iso:"ATE0Q0V1X1F0R1S45=3&P0&K3", 180)
        if not configured {
            ; A cold physical ESP32 sometimes emits its complete startup
            ; banner after Ctrl-C instead of answering this first command.
            ; The user's next manual DETECT then succeeds, so perform that
            ; same settled retry here and make one button press sufficient.
            delay_frames(15)
            flush_receiver()
            configured = send_command(
                iso:"ATE0Q0V1X1F0R1S45=3&P0&K3", 180)
        }
        if not configured {
            ; On this dedicated network port, receiving any bytes after the
            ; ZiModem setup request proves that the ESP32 side is alive. Some
            ; v4.0.2 startup paths produce a banner/READY response instead of
            ; the conventional result code. Allow the app to continue so the
            ; real Scan/Join commands can report their own results.
            if response_length > 0 {
                modem_present = true
                return true
            }
            return false
        }

        ; The successful ZiModem-specific configuration command above is the
        ; actual readiness test. Do not make Scan/Join depend on ATI4 also
        ; returning a final OK: physical firmware 4.0.2 can answer this query
        ; with its identification/startup text ending in READY instead.
        modem_present = true

        ; Ask for identification only to leave useful firmware information in
        ; the diagnostic panel. Its result must never undo confirmed readiness.
        void send_command(iso:"ATI4", 180)
        return true
    }
}
