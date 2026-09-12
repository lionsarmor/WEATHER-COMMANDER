; Streaming zlib decoder, bank 24. The PNG reader in bank 3 supplies input.
; The 32 KiB history lives in RAM banks 26..29, never in the resident app.
direct_inflate_mailbox {
    &ubyte character=$6f00
    &ubyte error=$6f01
    &uword count=$6f02
    &uword requested=$6f04
    &uword remaining=$6f06
    &ubyte remaining_high=$6f08
    &bool complete=$6f09
    const uword OUTPUT=$7000
}
