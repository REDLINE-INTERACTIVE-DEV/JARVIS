# JARVIS — Your local-first personal AI

Foundation includes a FastAPI local API, SQLite persistent memory, an optional llama.cpp GGUF brain, a gated computer-control layer, task engine, Android Jetpack Compose client, desktop client, pytest tests, and CI build artifacts.

Set JARVIS_MODEL_PATH to a local GGUF model to enable the local LLM. Model files are not committed. Without one, the API remains usable in foundation mode.

Android voice input uses SpeechRecognizer and voice output uses TextToSpeech. Android emulator access to a host backend is http://10.0.2.2:8000; a physical device should use the host LAN address.

Destructive computer actions require explicit confirmation and are not executed by the foundation until an OS-specific executor is implemented.