%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import network
main {
    %jmptable (network.action, network.weather, network.radar, network.city)
    sub start() { }
}
