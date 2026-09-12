%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import home
main {
    %jmptable (home.draw, home.choose, home.tick)
    sub start() { }
}
