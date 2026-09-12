%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import forecast

main {
    %jmptable (forecast.draw)
    sub start() { }
}
