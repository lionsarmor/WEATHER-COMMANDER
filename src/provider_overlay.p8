%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import provider

main {
    %jmptable (provider.refresh, provider.check_age)
    sub start() { }
}
