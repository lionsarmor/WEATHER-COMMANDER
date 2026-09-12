%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import cities

main {
    %jmptable (cities.draw, cities.panel)
    sub start() { }
}
