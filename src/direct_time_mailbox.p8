; UTC is derived from the provider's HTTP Date, independently of RTC timezone.
direct_time_mailbox {
    &uword low=$6ff2
    &uword high=$6ff4
    &uword year=$6ff6
    &ubyte month=$6ff8
    &ubyte day=$6ff9
    &ubyte hour=$6ffa
    &ubyte minute=$6ffb
    &ubyte second=$6ffc
    &bool valid=$6ffd
}
