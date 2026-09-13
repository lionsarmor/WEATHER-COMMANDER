%import network_driver
%import network_mailbox
%import strings
%import direct_geo
%import direct_weather_mailbox
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
        network_mailbox.connection=2
        message(iso:"NOT CONNECTED / SCAN OR ENTER SSID")
        void network_driver.send_command(iso:"ATI2",180)
        ; Trust an assigned address, not a generic OK line.
        if network_driver.response_contains(iso:"0.0.0.0") return
        if network_driver.response_length<7 return
        for i in 1 to network_driver.response_length-1 {
            if network_driver.response[i]==46 and network_driver.response[i-1]>=48 and network_driver.response[i-1]<=57 {
                network_mailbox.connection=3
                message(iso:"WI-FI CONNECTED / READY FOR WEATHER")
                return
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
                void network_driver.send_command(iso:"ATW10",900)
                network_driver.end_network_capture()
                message(iso:"SELECT A NETWORK OR ENTER ITS NAME")
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
                void network_driver.send_command(command,900)
                clear_secret()
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
        direct_weather_mailbox.country=state.country
        if state.country_status==3 direct_weather_mailbox.country=state.country_choice
        direct_weather_fetch()
        if network_mailbox.complete network_mailbox.connection=3
    }
    sub radar() {
        direct_radar_mailbox.downloaded=false
        if not ready() return
        direct_radar_mailbox.country=state.country
        direct_radar_download()
    }
    sub city() { direct_geo.send() }
}
