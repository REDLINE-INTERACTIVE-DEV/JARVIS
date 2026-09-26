"""Optional desktop STT/TTS adapters; the core GUI remains dependency-light."""
class VoiceUnavailable(RuntimeError):
    pass

def speak(text: str) -> None:
    try:
        import pyttsx3
    except ImportError as exc:
        raise VoiceUnavailable("Install desktop/requirements-voice.txt for TTS.") from exc
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def listen() -> str:
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise VoiceUnavailable("Install desktop/requirements-voice.txt for STT.") from exc
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)
    return recognizer.recognize_google(audio)
