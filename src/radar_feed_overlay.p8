%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import radar_feed
main {
    %jmptable (radar_feed.refresh, radar_feed.age, radar_feed.step, radar_feed.cancel, radar_feed.restore)
    sub start() { }
}
