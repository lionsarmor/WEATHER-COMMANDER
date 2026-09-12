; JSON values point into the bounded native HTTP body; no banked pointers escape.
direct_json_mailbox {
    &ubyte[96] text=$6e00
    &uword position=$6e60
    &uword start=$6e62
    &uword end=$6e64
    &ubyte kind=$6e66
    &bool error=$6e67
    &ubyte length=$6e68
    &uword scope=$6e6a
    &bool found=$6e6c
    &ubyte[48] key=$6e80
}
