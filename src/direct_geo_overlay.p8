%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_geo
main {
    %jmptable (direct_geo.send)
    sub start() { }
}
