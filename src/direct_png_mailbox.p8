; Native PNG scanlines are exposed at $7001, with at most 1536 bytes per row.
; Decode every row and require complete before committing any radar pixels.
direct_png_mailbox {
    &uword width=$6f10
    &uword height=$6f12
    &uword row_bytes=$6f14
    &ubyte channels=$6f16
    &ubyte color=$6f17
    &uword row=$6f18
    &bool ready=$6f1a
    &bool complete=$6f1b
    &uword pixel=$6f1c
    &ubyte red=$6f1e
    &ubyte green=$6f1f
    &ubyte blue=$6f20
    &ubyte alpha=$6f21
}
