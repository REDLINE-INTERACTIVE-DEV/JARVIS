# JARVIS — Your local-first personal AI

Foundation includes a FastAPI local API, SQLite persistent memory, an optional llama.cpp GGUF brain, a gated computer-control layer, task engine, Android Jetpack Compose client, desktop client, pytest tests, and CI build artifacts.

Install backend/requirements.txt for CI-safe API tests. Install backend/requirements-llama.txt on a machine that has a compatible compiler/toolchain to enable the optional local GGUF brain through JARVIS_MODEL_PATH.

Android voice input uses SpeechRecognizer and voice output uses TextToSpeech. Android emulator access to a host backend is http://10.0.2.2:8000; a physical device should use the host LAN address.

Destructive computer actions require explicit confirmation and are not executed by the foundation until an OS-specific executor is implemented.

This is a foundation, not a release: real OS tool executors, richer task planning/verification, desktop voice, production networking/authentication, and release signing still need to be implemented and tested.