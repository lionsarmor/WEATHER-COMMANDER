%import direct_crypto_mailbox

; SHA-256 and HMAC-SHA-256, per RFC 6234 sections 4..7 and RFC 2104.
; 32-bit values are pairs of 16-bit words; no floating point or host helper.
direct_crypto {
    uword[8] initial_hi=[$6a09,$bb67,$3c6e,$a54f,$510e,$9b05,$1f83,$5be0]
    uword[8] initial_lo=[$e667,$ae85,$f372,$f53a,$527f,$688c,$d9ab,$cd19]
    uword[64] k_hi=[$428a,$7137,$b5c0,$e9b5,$3956,$59f1,$923f,$ab1c,$d807,$1283,$2431,$550c,$72be,$80de,$9bdc,$c19b,$e49b,$efbe,$0fc1,$240c,$2de9,$4a74,$5cb0,$76f9,$983e,$a831,$b003,$bf59,$c6e0,$d5a7,$06ca,$1429,$27b7,$2e1b,$4d2c,$5338,$650a,$766a,$81c2,$9272,$a2bf,$a81a,$c24b,$c76c,$d192,$d699,$f40e,$106a,$19a4,$1e37,$2748,$34b0,$391c,$4ed8,$5b9c,$682e,$748f,$78a5,$84c8,$8cc7,$90be,$a450,$bef9,$c671]
    uword[64] k_lo=[$2f98,$4491,$fbcf,$dba5,$c25b,$11f1,$82a4,$5ed5,$aa98,$5b01,$85be,$7dc3,$5d74,$b1fe,$06a7,$f174,$69c1,$4786,$9dc6,$a1cc,$2c6f,$84aa,$a9dc,$88da,$5152,$c66d,$27c8,$7fc7,$0bf3,$9147,$6351,$2967,$0a85,$2138,$6dfc,$0d13,$7354,$0abb,$c92e,$2c85,$e8a1,$664b,$8b70,$51a3,$e819,$0624,$3585,$a070,$c116,$6c08,$774c,$bcb5,$0cb3,$aa4a,$ca4f,$6ff3,$82ee,$636f,$7814,$0208,$fffa,$6ceb,$a3f7,$78f2]
    uword[8] state_lo
    uword[8] state_hi
    uword[8] work_lo
    uword[8] work_hi
    uword[16] schedule_lo
    uword[16] schedule_hi
    ubyte[64] key_block
    ubyte[32] inner
    ubyte[4] rotate_a=[7,17,2,6]
    ubyte[4] rotate_b=[18,19,13,11]
    ubyte[4] rotate_c=[3,10,22,25]
    uword acc_lo
    uword acc_hi
    uword rotate_lo
    uword rotate_hi
    uword sigma_lo
    uword sigma_hi
    ubyte position
    uword bytes

    sub add(uword low,uword high) {
        if low>65535-acc_lo acc_hi++
        acc_lo+=low
        acc_hi+=high
    }
    sub rotate(ubyte count,bool logical) {
        bool bit
        repeat count {
            bit=rotate_lo & 1!=0
            rotate_lo>>=1
            if rotate_hi & 1!=0 rotate_lo|=$8000
            rotate_hi>>=1
            if bit and not logical rotate_hi|=$8000
        }
    }
    sub sigma(uword low,uword high,ubyte kind) {
        rotate_lo=low
        rotate_hi=high
        rotate(rotate_a[kind],false)
        sigma_lo=rotate_lo
        sigma_hi=rotate_hi
        rotate_lo=low
        rotate_hi=high
        rotate(rotate_b[kind],false)
        sigma_lo^=rotate_lo
        sigma_hi^=rotate_hi
        rotate_lo=low
        rotate_hi=high
        rotate(rotate_c[kind],kind<2)
        sigma_lo^=rotate_lo
        sigma_hi^=rotate_hi
    }
    sub transform() {
        ubyte i
        ubyte j
        ubyte k
        uword first_lo
        uword first_hi
        uword second_lo
        uword second_hi
        for i in 0 to 7 {
            work_lo[i]=state_lo[i]
            work_hi[i]=state_hi[i]
        }
        for i in 0 to 63 {
            k=i & 15
            if i>=16 {
                j=(i+1) & 15
                sigma(schedule_lo[j],schedule_hi[j],0)
                acc_lo=sigma_lo
                acc_hi=sigma_hi
                j=(i+14) & 15
                sigma(schedule_lo[j],schedule_hi[j],1)
                add(sigma_lo,sigma_hi)
                add(schedule_lo[k],schedule_hi[k])
                j=(i+9) & 15
                add(schedule_lo[j],schedule_hi[j])
                schedule_lo[k]=acc_lo
                schedule_hi[k]=acc_hi
            }
            sigma(work_lo[4],work_hi[4],3)
            acc_lo=sigma_lo
            acc_hi=sigma_hi
            add(work_lo[7],work_hi[7])
            first_lo=(work_lo[4] & work_lo[5]) ^ ((work_lo[4] ^ $ffff) & work_lo[6])
            first_hi=(work_hi[4] & work_hi[5]) ^ ((work_hi[4] ^ $ffff) & work_hi[6])
            add(first_lo,first_hi)
            add(k_lo[i],k_hi[i])
            add(schedule_lo[k],schedule_hi[k])
            first_lo=acc_lo
            first_hi=acc_hi
            sigma(work_lo[0],work_hi[0],2)
            acc_lo=sigma_lo
            acc_hi=sigma_hi
            second_lo=(work_lo[0] & work_lo[1]) ^ (work_lo[0] & work_lo[2]) ^ (work_lo[1] & work_lo[2])
            second_hi=(work_hi[0] & work_hi[1]) ^ (work_hi[0] & work_hi[2]) ^ (work_hi[1] & work_hi[2])
            add(second_lo,second_hi)
            second_lo=acc_lo
            second_hi=acc_hi
            for j in 7 downto 1 {
                work_lo[j]=work_lo[j-1]
                work_hi[j]=work_hi[j-1]
            }
            acc_lo=work_lo[4]
            acc_hi=work_hi[4]
            add(first_lo,first_hi)
            work_lo[4]=acc_lo
            work_hi[4]=acc_hi
            acc_lo=first_lo
            acc_hi=first_hi
            add(second_lo,second_hi)
            work_lo[0]=acc_lo
            work_hi[0]=acc_hi
        }
        for i in 0 to 7 {
            acc_lo=state_lo[i]
            acc_hi=state_hi[i]
            add(work_lo[i],work_hi[i])
            state_lo[i]=acc_lo
            state_hi[i]=acc_hi
        }
    }
    sub initialize() {
        ubyte i
        for i in 0 to 7 {
            state_lo[i]=initial_lo[i]
            state_hi[i]=initial_hi[i]
        }
        position=0
        bytes=0
    }
    sub feed(ubyte value) {
        ubyte index=position>>2
        when position & 3 {
            0 -> schedule_hi[index]=(value as uword)*256
            1 -> schedule_hi[index]=mkword(msb(schedule_hi[index]),value)
            2 -> schedule_lo[index]=(value as uword)*256
            3 -> schedule_lo[index]=mkword(msb(schedule_lo[index]),value)
        }
        position++
        bytes++
        if position==64 { transform()
            position=0 }
    }
    sub finish() {
        ubyte i
        uword bit_length=bytes*8
        feed(128)
        while position!=56 feed(0)
        repeat 6 feed(0)
        feed(msb(bit_length))
        feed(lsb(bit_length))
        for i in 0 to 7 {
            direct_crypto_mailbox.digest[i*4]=msb(state_hi[i])
            direct_crypto_mailbox.digest[i*4+1]=lsb(state_hi[i])
            direct_crypto_mailbox.digest[i*4+2]=msb(state_lo[i])
            direct_crypto_mailbox.digest[i*4+3]=lsb(state_lo[i])
        }
    }
    sub message() {
        uword i=0
        while i<direct_crypto_mailbox.length {
            feed(@(direct_crypto_mailbox.pointer+i))
            i++
        }
    }
    sub allowed() -> bool {
        return direct_crypto_mailbox.length<=4096 and direct_crypto_mailbox.pointer>=$7000 and direct_crypto_mailbox.pointer<=$9800-direct_crypto_mailbox.length
    }
    sub hash() {
        direct_crypto_mailbox.valid=false
        if not allowed() return
        initialize()
        message()
        finish()
        direct_crypto_mailbox.valid=true
    }
    sub hmac() {
        ubyte i
        direct_crypto_mailbox.valid=false
        if not allowed() or direct_crypto_mailbox.key_length>96 return
        for i in 0 to 63 key_block[i]=0
        if direct_crypto_mailbox.key_length>64 {
            initialize()
            for i in 0 to direct_crypto_mailbox.key_length-1 feed(direct_crypto_mailbox.key[i])
            finish()
            for i in 0 to 31 key_block[i]=direct_crypto_mailbox.digest[i]
        } else {
            i=0
            while i<direct_crypto_mailbox.key_length {
                key_block[i]=direct_crypto_mailbox.key[i]
                i++
            }
        }
        initialize()
        for i in 0 to 63 feed(key_block[i] ^ $36)
        message()
        finish()
        for i in 0 to 31 inner[i]=direct_crypto_mailbox.digest[i]
        initialize()
        for i in 0 to 63 feed(key_block[i] ^ $5c)
        for i in 0 to 31 feed(inner[i])
        finish()
        direct_crypto_mailbox.valid=true
        for i in 0 to 63 key_block[i]=0
    }
}
