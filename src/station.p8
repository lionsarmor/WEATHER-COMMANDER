%import syslib
%import state

; Each landscape lives in its own data bank. The resident core streams the
; requested bank into tiles 768..957; this module owns only the scene map.
station {
    ubyte previous=255
    sub draw() {
        ubyte phase=3
        ubyte row
        ubyte col
        uword tile=768
        uword destination=$ab78
        if state.hour>=5 and state.hour<8 phase=0
        else if state.hour>=8 and state.hour<17 phase=1
        else if state.hour>=17 and state.hour<20 phase=2
        state.scene_bank=36+state.scenery*4+phase
        if phase==previous return
        for row in 0 to 9 {
            %asm {{ php
                sei }}
            cx16.VERA_CTRL=0
            cx16.VERA_ADDR_L=lsb(destination)
            cx16.VERA_ADDR_M=msb(destination)
            cx16.VERA_ADDR_H=$10
            for col in 0 to 18 {
                cx16.VERA_DATA0=lsb(tile)
                cx16.VERA_DATA0=msb(tile)|((11+phase)<<4)
                tile++
            }
            %asm {{ plp }}
            destination+=256
        }
        previous=phase
    }
}
