%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_png
main {
    %jmptable (direct_png.open, direct_png.next_row, direct_png.input_byte, direct_png.close, direct_png.pixel)
    sub start() { }
}
