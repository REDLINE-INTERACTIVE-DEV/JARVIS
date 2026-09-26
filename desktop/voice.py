"""Optional desktop STT/TTS adapters with a cinematic assistant profile."""
class VoiceUnavailable(RuntimeError):
    pass


def speak(text: str) -> None:
    try:
        import pyttsx3
    except ImportError as exc:
        raise VoiceUnavailable("Install desktop/requirements-voice.txt for TTS.") from exc

    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices") or []
    preferred = next(
        (
            voice.id
            for voice in voices
            if "en_gb" in voice.id.lower()
            or "english_rp" in voice.id.lower()
            or "british" in voice.name.lower()
        ),
        None,
    )
    if preferred:
        engine.setProperty("voice", preferred)
    engine.say(text)
    engine.runAndWait()


def listen() -> str:
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise VoiceUnavailable("Install desktop/requirements-voice.txt for STT.") from exc
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)
    return recognizer.recognize_google(audio)
