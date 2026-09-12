%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import wifi
main {
    %jmptable (wifi.draw, wifi.key, wifi.click, wifi.hit)
    sub start() { }
}
