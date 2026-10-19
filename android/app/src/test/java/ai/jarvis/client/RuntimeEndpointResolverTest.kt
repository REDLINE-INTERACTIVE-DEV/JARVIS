package ai.jarvis.client

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RuntimeEndpointResolverTest {
    @Test fun acceptsPublicHttpsEndpoint() {
        assertTrue(RuntimeEndpointResolver.isUsable("https://sample.trycloudflare.com"))
    }
    @Test fun rejectsPlainHttpEndpoint() {
        assertFalse(RuntimeEndpointResolver.isUsable("http://sample.trycloudflare.com"))
    }
    @Test fun rejectsLoopbackAndPrivateEndpoints() {
        listOf("https://localhost:8000", "https://127.0.0.1:8000",
            "https://192.168.1.20:8000", "https://10.0.2.2:8000")
            .forEach { assertFalse(RuntimeEndpointResolver.isUsable(it)) }
    }
    @Test fun rejectsCredentialsQueryAndFragment() {
        listOf("https://user:pass@sample.trycloudflare.com",
            "https://sample.trycloudflare.com/?token=secret",
            "https://sample.trycloudflare.com/#token")
            .forEach { assertFalse(RuntimeEndpointResolver.isUsable(it)) }
    }
}
