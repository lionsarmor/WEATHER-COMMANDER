%address $a000
%memtop $c000
%output library
%zeropage basicsafe
%import direct_crypto
%import direct_time
main {
    %jmptable (direct_crypto.hmac, direct_crypto.hash, direct_time.date, direct_time.parse, direct_time.format)
    sub start() { }
}
