%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_weather_decode
main {
    %jmptable (direct_weather_decode.decode, direct_json.validate, direct_json.find, direct_json.next, direct_json.skip)
    sub start() { }
}
