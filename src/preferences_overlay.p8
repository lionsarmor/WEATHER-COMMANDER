%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import preferences
main {
    %jmptable (preferences.load, preferences.save)
    sub start() { }
}
