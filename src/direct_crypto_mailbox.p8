; Public PAGASA session signing. These are ephemeral public grants, not
; account credentials, and are never written to the user's settings file.
direct_crypto_mailbox {
    &ubyte[96] key=$6f40
    &ubyte[32] digest=$6fa0
    &ubyte[32] nonce=$6fc0
    &ubyte[12] timestamp=$6fe0
    &ubyte key_length=$6fec
    &uword length=$6fed
    &uword pointer=$6fef
    &bool valid=$6ff1
}
