package app.spindle

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class ServerAddressTest {
    private fun ok(raw: String) = assertNull(raw, ServerAddress.problem(Credentials.normalizeServer(raw)))
    private fun refused(raw: String) = assertNotNull(raw, ServerAddress.problem(Credentials.normalizeServer(raw)))

    @Test fun homeNetworkAddressesMayUseHttp() {
        ok("192.168.1.20:4533"); ok("http://192.168.0.5:4533/"); ok("http://10.0.0.8:4533"); ok("http://172.20.1.2:4533")
    }

    @Test fun tailscaleStillWorks() {
        ok("http://music-phone.tail1234.ts.net:4533"); ok("http://100.101.102.103:4533")
    }

    @Test fun httpsWorksAnywhere() {
        ok("https://music.example.com"); ok("https://203.0.113.9:4533")
    }

    @Test fun plainHttpToTheInternetIsRefused() {
        refused("http://music.example.com"); refused("http://8.8.8.8:4533"); refused("http://172.32.0.1:4533"); refused("http://192.169.1.1")
        refused(""); refused("http://")
    }

    @Test fun addressIsTidied() {
        assertEquals("http://192.168.1.20:4533", Credentials.normalizeServer(" 192.168.1.20:4533/rest/ "))
    }
}
