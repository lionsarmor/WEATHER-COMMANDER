direct_render_mailbox {
    &ubyte phase=$6f2c          ; 0 idle, 1 decode rows, 2 ready to pack, 3 done, 4 failed
    &ubyte step=$6f2d          ; final spatial simplification: 1, 2, 4 or 8 pixels
}
