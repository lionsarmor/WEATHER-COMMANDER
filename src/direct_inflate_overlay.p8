%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_inflate
main {
    %jmptable (direct_inflate.initialize, direct_inflate.pull)
    sub start() { }
}
