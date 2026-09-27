package ai.jarvis.client

data class WakeMatch(val command: String?)

object WakePhraseMatcher {
    private val wakeRegex = Regex(
        """^\s*(?:hey\s+)?jarvis(?:\b|[,.:;!?-])(.*)$""",
        RegexOption.IGNORE_CASE,
    )

    fun match(raw: String): WakeMatch? {
        val phrase = raw.trim().replace(Regex("""\s+"""), " ")
        val match = wakeRegex.matchEntire(phrase) ?: return null
        val command = match.groupValues.getOrNull(1)
            .orEmpty()
            .trimStart(',', '.', ':', ';', '-', ' ')
            .trim()
        return WakeMatch(command.ifBlank { null })
    }
}
