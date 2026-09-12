%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_radar
main {
    %jmptable (direct_radar.download, direct_radar.metadata, direct_radar.session, direct_radar.sign)
    sub start() { }
}
