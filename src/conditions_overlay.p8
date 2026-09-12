%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import conditions

main {
    %jmptable (conditions.draw)
    sub start() { }
}
