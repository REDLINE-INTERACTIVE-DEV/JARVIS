package ai.jarvis.client.screen

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenActionParserTest {
    @Test fun parsesActionsWithJsonWhitespace() {
        val actions = ScreenActionParser.parseActions("""{"actions": [ {"action_id": 7, "action": "tap", "arguments": {"x": 12, "y": 34}} ]}""")
        assertEquals(1, actions.size)
        assertEquals("tap", actions[0].action)
        assertEquals(12f, ScreenActionParser.number(actions[0].arguments, "x")!!)
        assertEquals(34f, ScreenActionParser.number(actions[0].arguments, "y")!!)
    }

    @Test fun parsesMultipleActionsInOrder() {
        val actions = ScreenActionParser.parseActions("""{"actions":[{"action":"back","arguments":{}},{"action":"home","arguments":{}},{"action":"recents","arguments":{}}]}""")
        assertEquals(listOf("back", "home", "recents"), actions.map { it.action })
    }

    @Test fun parsesDecimalSwipeCoordinates() {
        val action = ScreenActionParser.parseActions("""{"actions":[{"action":"swipe","arguments":{"x1":1.5,"y1":2.5,"x2":3.5,"y2":4.5}}]}""").single()
        assertEquals(1.5f, ScreenActionParser.number(action.arguments, "x1")!!)
        assertEquals(4.5f, ScreenActionParser.number(action.arguments, "y2")!!)
    }

    @Test fun preservesEscapedTypeText() {
        val action = ScreenActionParser.parseActions("""{"actions":[{"action":"type","arguments":{"text":"Hello \"JARVIS\""}}]}""").single()
        assertEquals("Hello \"JARVIS\"", ScreenActionParser.string(action.arguments, "text"))
    }

    @Test fun ignoresItemsWithoutAnAction() {
        val actions = ScreenActionParser.parseActions("""{"actions":[{"arguments":{"x":1}},{"action":"tap","arguments":{"x":2,"y":3}}]}""")
        assertEquals(1, actions.size)
        assertEquals("tap", actions.single().action)
    }

    @Test fun missingActionsReturnsEmptyList() {
        assertTrue(ScreenActionParser.parseActions("""{"status":"ok"}""").isEmpty())
    }

    @Test fun malformedJsonReturnsEmptyList() {
        assertTrue(ScreenActionParser.parseActions("""{"actions":""").isEmpty())
    }

    @Test fun missingOrNullNumberReturnsNull() {
        val arguments = JSONObject("""{"x":null}""")
        assertNull(ScreenActionParser.number(arguments, "x"))
        assertNull(ScreenActionParser.number(arguments, "y"))
    }

    @Test fun nonNumericCoordinateReturnsNull() {
        assertNull(ScreenActionParser.number(JSONObject("""{"x":"north"}"""), "x"))
    }

    @Test fun missingStringReturnsNullAndEscapedStringDecodes() {
        val arguments = JSONObject("""{"text":"line1\nline2"}""")
        assertNull(ScreenActionParser.string(arguments, "missing"))
        assertEquals("line1\nline2", ScreenActionParser.string(arguments, "text"))
    }
}
