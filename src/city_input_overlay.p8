%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import city_input
main {
    %jmptable (city_input.draw, city_input.key, city_input.hit, city_input.click, city_input.send, city_input.tick)
    sub start() { }
}
