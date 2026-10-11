package ai.jarvis.client

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RuntimeEndpointResolverTest {
    @Test
    fun acceptsValidHttpAndHttpsBackendUrls() {
        assertTrue(RuntimeEndpointResolver.isUsable("https://jarvis.example.com"))
        assertTrue(RuntimeEndpointResolver.isUsable("http://192.168.1.20:8000"))
    }

    @Test
    fun rejectsMalformedOrUnsupportedUrls() {
        assertFalse(RuntimeEndpointResolver.isUsable(""))
        assertFalse(RuntimeEndpointResolver.isUsable("http://"))
        assertFalse(RuntimeEndpointResolver.isUsable("file:///tmp/jarvis"))
        assertFalse(RuntimeEndpointResolver.isUsable("ftp://jarvis.example.com"))
    }

    @Test
    fun rejectsPhoneLoopbackAndEmulatorOnlyAddresses() {
        assertFalse(RuntimeEndpointResolver.isUsable("http://localhost:8000"))
        assertFalse(RuntimeEndpointResolver.isUsable("http://127.0.0.1:8000"))
        assertFalse(RuntimeEndpointResolver.isUsable("http://10.0.2.2:8000"))
    }
}
