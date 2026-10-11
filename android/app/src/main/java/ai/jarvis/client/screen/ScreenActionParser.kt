package ai.jarvis.client.screen

import org.json.JSONObject

internal data class ParsedScreenAction(
    val action: String,
    val arguments: JSONObject,
)

internal object ScreenActionParser {
    fun parseActions(response: String): List<ParsedScreenAction> {
        return try {
            val actions = JSONObject(response).optJSONArray("actions") ?: return emptyList()
            buildList {
                for (index in 0 until actions.length()) {
                    val item = actions.optJSONObject(index) ?: continue
                    val action = item.optString("action").trim()
                    if (action.isNotEmpty()) {
                        add(ParsedScreenAction(action, item.optJSONObject("arguments") ?: JSONObject()))
                    }
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun number(arguments: JSONObject, key: String): Float? {
        return try {
            if (!arguments.has(key) || arguments.isNull(key)) null
            else arguments.getDouble(key).toFloat().takeIf { it.isFinite() }
        } catch (_: Exception) {
            null
        }
    }

    fun string(arguments: JSONObject, key: String): String? {
        return try {
            if (!arguments.has(key) || arguments.isNull(key)) null
            else arguments.getString(key)
        } catch (_: Exception) {
            null
        }
    }
}
