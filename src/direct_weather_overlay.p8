%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_weather
main {
    %jmptable (direct_weather.fetch, direct_weather.invalidate, direct_weather.request)
    sub start() { }
}
