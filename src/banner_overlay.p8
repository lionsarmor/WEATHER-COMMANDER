%address $a000
%memtop $ae80
%output library
%zeropage basicsafe
%import banner
main {
    %jmptable (banner.draw)
    sub start() { }
}
