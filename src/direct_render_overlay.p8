%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_render
main {
    %jmptable (direct_render.begin, direct_render.next, direct_render.pack, direct_render.cancel)
    sub start() { }
}
