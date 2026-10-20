package ai.jarvis.client

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RuntimeEndpointResolverTest {
    @Test
    fun acceptsOnlyHttpsPublicEndpoints() {
        assertTrue(RuntimeEndpointResolver.isUsable("https://sample.trycloudflare.com"))
        assertFalse(RuntimeEndpointResolver.isUsable("http://sample.trycloudflare.com"))
        assertFalse(RuntimeEndpointResolver.isUsable("https://localhost:8000"))
        assertFalse(RuntimeEndpointResolver.isUsable("https://127.0.0.1:8000"))
        assertFalse(RuntimeEndpointResolver.isUsable("https://10.0.2.2:8000"))
        assertFalse(RuntimeEndpointResolver.isUsable("https://user:pass@sample.trycloudflare.com"))
        assertFalse(RuntimeEndpointResolver.isUsable("not-a-url"))
    }
}
