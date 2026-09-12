%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import radar

main {
    %jmptable (radar.draw, radar.animate)
    sub start() { }
}
