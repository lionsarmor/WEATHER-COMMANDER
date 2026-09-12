%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import settings

main {
    %jmptable (settings.draw)
    sub start() { }
}
