%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import map

main {
    %jmptable (map.draw, map.local)
    sub start() { }
}
