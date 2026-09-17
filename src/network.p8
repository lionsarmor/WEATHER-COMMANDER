%import network_driver
%import network_mailbox
%import strings
%import direct_geo
%import direct_weather_mailbox
%import direct_http_mailbox
%import direct_radar_mailbox
%import state

network {
    ubyte[255] command
    sub message(str value) { void strings.copy(value,network_mailbox.notice) }
    sub ready() -> bool {
        if network_driver.modem_present return true
        if network_driver.detect_modem() {
            network_mailbox.connection=2
            return true
        }
        network_mailbox.connection=1
        message(iso:"NO WI-FI MODEM FOUND")
        return false
    }
    sub status() {
        ubyte i
        ubyte ch
        ubyte parts=0
        ubyte digits=0
        uword octet=0
        bool valid=true
        bool nonzero=false
        network_mailbox.connection=2
        message(iso:"NOT CONNECTED / SCAN OR ENTER SSID")
        void network_driver.send_command(iso:"ATI2",180)
        ; A full IPv4 line is required. Firmware versions such as 4.0.2 and
        ; echoed text containing a digit followed by '.' are not addresses.
        for i in 0 to network_driver.response_length {
            ch=network_driver.response[i]
            if ch==13 or ch==10 or ch==0 {
                if valid and parts==3 and digits>0 and nonzero {
                    network_mailbox.connection=3
                    message(iso:"WI-FI CONNECTED / READY FOR WEATHER")
                    return
                }
                parts=0
                digits=0
                octet=0
                valid=true
                nonzero=false
            } else if ch>=48 and ch<=57 {
                if digits>=3 valid=false
                else {
                    octet=octet*10+ch-48
                    digits++
                    if octet>255 valid=false
                    if octet>0 nonzero=true
                }
            } else if ch==46 and digits>0 and parts<3 {
                parts++
                digits=0
                octet=0
            } else {
                valid=false
            }
        }
        message(iso:"NOT CONNECTED / SCAN OR ENTER SSID")
    }
    sub clear_secret() {
        ubyte i
        for i in 0 to 63 network_mailbox.password[i]=0
        for i in 0 to 179 command[i]=0
        for i in 0 to 255 network_driver.response[i]=0
        network_driver.response_length=0
    }
    sub action() {
        ubyte i
        ubyte p
        ubyte request=network_mailbox.action
        bool joined
        network_mailbox.action=0
        if request==5 { network_driver.modem_present=false
            network_mailbox.connection=0
            clear_secret()
            message(iso:"WEATHER OFFLINE / DEMO SELECTED")
            return }
        if not ready() { clear_secret()
            return }
        when request {
            1 -> {
                network_driver.begin_network_capture()
                joined=network_driver.send_command(iso:"ATW10",900)
                network_driver.end_network_capture()
                if joined message(iso:"SELECT A NETWORK OR ENTER ITS NAME")
                else message(iso:"SCAN FAILED / TRY AGAIN OR ENTER SSID")
            }
            2,4 -> status()
            3 -> {
                ; A failed new join must not inherit the previous network's
                ; connected flag and advance the setup wizard accidentally.
                network_mailbox.connection=2
                if network_mailbox.ssid[0]==0 { message(iso:"ENTER OR SELECT A NETWORK FIRST")
                    return }
                ; Echo must be disabled before transmitting a credential.
                if not network_driver.send_command(iso:"ATE0",180) {
                    clear_secret()
                    message(iso:"MODEM NOT RESPONDING / TRY SCAN AGAIN")
                    return
                }
                void strings.copy(iso:"ATW\"",command)
                p=4
                for i in 0 to 31 {
                    if network_mailbox.ssid[i]==0 break
                    command[p]=network_mailbox.ssid[i]
                    p++
                }
                command[p]=44
                p++
                for i in 0 to 62 {
                    if network_mailbox.password[i]==0 break
                    command[p]=network_mailbox.password[i]
                    p++
                }
                command[p]=34
                command[p+1]=0
                joined=network_driver.send_command(command,900)
                clear_secret()
                if not joined { message(iso:"COULD NOT JOIN / CHECK YOUR PASSWORD")
                    return }
                status()
                if network_mailbox.connection!=3 message(iso:"COULD NOT JOIN / CHECK YOUR PASSWORD")
            }
        }
    }
    extsub @bank 22 $a003 = direct_weather_fetch()
    extsub @bank 1 $a003 = direct_radar_download()
    sub weather() {
        network_mailbox.complete=false
        network_mailbox.received=0
        if not ready() return
        if network_mailbox.connection!=3 {
            status()
            if network_mailbox.connection!=3 return
        }
        direct_weather_mailbox.country=state.country
        if state.country_status==3 direct_weather_mailbox.country=state.country_choice
        direct_weather_fetch()
        if network_mailbox.complete network_mailbox.connection=3
        else if direct_http_mailbox.error==2 message(iso:"HTTPS FAILED / CHECK TLS OR INTERNET")
        else if direct_http_mailbox.status==429 message(iso:"WEATHER API BUSY / TRY AGAIN LATER")
        else if direct_http_mailbox.status!=200 message(iso:"WEATHER API UNREACHABLE / TRY AGAIN")
        else if not direct_http_mailbox.complete message(iso:"DOWNLOAD FAILED / CHECK INTERNET")
        else message(iso:"WEATHER FORMAT ERROR / TRY LATER")
    }
    sub radar() {
        direct_radar_mailbox.downloaded=false
        if not ready() return
        if network_mailbox.connection!=3 return
        direct_radar_mailbox.country=state.country
        direct_radar_download()
    }
    sub city() { direct_geo.send() }
}
