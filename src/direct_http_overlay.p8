%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_http
main {
    %jmptable (direct_http.get, direct_http.reset, direct_http.feed)
    sub start() { }
}
