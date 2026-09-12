%address $a000
%memtop $a800
%output library
%zeropage basicsafe
%import station

main {
    %jmptable (station.draw)
    sub start() { }
}
