package ai.jarvis.client

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class WakePhraseMatcherTest {
    @Test
    fun accepts_jarvis_and_hey_jarvis_forms() {
        assertNull(WakePhraseMatcher.match("hello there"))
        assertEquals(null, WakePhraseMatcher.match("jarvis")?.command)
        assertEquals(null, WakePhraseMatcher.match("Hey JARVIS")?.command)
        assertEquals("open my calendar", WakePhraseMatcher.match("JARVIS, open my calendar")?.command)
        assertEquals("open my calendar", WakePhraseMatcher.match("hey jarvis open my calendar")?.command)
        assertEquals("what is the time", WakePhraseMatcher.match("JARVIS: what is the time")?.command)
    }

    @Test
    fun rejects_random_mentions() {
        assertNull(WakePhraseMatcher.match("I was talking about jarvis yesterday"))
        assertNull(WakePhraseMatcher.match("jarvisian"))
        assertNull(WakePhraseMatcher.match("please tell me about JARVIS technology"))
    }

    @Test
    fun runs_one_hundred_voice_phrase_cases() {
        val cases = buildList {
            repeat(50) { i ->
                add("JARVIS, run voice test command $i" to "run voice test command $i")
            }
            repeat(50) { i ->
                add("hey JARVIS, run voice test command $i" to "run voice test command $i")
            }
        }
        assertEquals(100, cases.size)
        cases.forEach { (spoken, expected) ->
            assertEquals(expected, WakePhraseMatcher.match(spoken)?.command)
        }
    }

    @Test
    fun ignores_one_hundred_non_wake_phrases() {
        repeat(100) { i ->
            assertNull(WakePhraseMatcher.match("this is ordinary speech $i"))
        }
    }
}
