%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import about

main {
    %jmptable (about.draw, about.help)
    sub start() { }
}
