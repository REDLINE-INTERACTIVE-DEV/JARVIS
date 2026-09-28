# JARVIS — Your local-first personal AI

JARVIS is a standalone personal assistant with a local-first foundation.

## Current foundation
- Independent local GGUF brain through llama.cpp when a model is supplied
- Persistent SQLite memory
- Structured tool registry with destructive-action confirmation gates
- Task engine with explicit planning/confirmation/execution/completion states
- Dependency-light web research/search subsystem
- Android Jetpack Compose client with typed chat, configurable API endpoint and speech input
- Android TextToSpeech output with a calm British-style assistant profile
- Animated JARVIS-style listening/thinking/speaking core visualization
- Lightweight desktop client with configurable API endpoint
- Optional desktop STT/TTS adapters
- Backend pytest suite with isolated temporary databases
- GitHub Actions for backend tests, Android APK, and Linux/Windows desktop packages

## Voice note
The movie JARVIS voice is a copyrighted performance associated with the Iron Man films. This project does not clone or reproduce that exact voice. Instead, the clients use a generic, calm British-style synthetic voice profile that keeps the cinematic assistant feel without impersonating the performer.

## Run backend
```bash
python -m pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Optional local brain
Install `backend/requirements-llama.txt`, provide a compatible GGUF model, and set `JARVIS_MODEL_PATH=/path/to/model.gguf`. Without a model, the API remains functional in foundation mode but does not provide full local language-model reasoning.

## Search
Use `POST /search` with a query, or say `search for <query>`, `search: <query>`, or `look up <query>` in chat. The default provider is DuckDuckGo's public HTML results and requires no API key. Set `JARVIS_SEARCH_URL` to point at a compatible search endpoint if you want to replace it.

## Android
The Android client does not use `127.0.0.1`, `localhost`, or emulator-only `10.0.2.2` as its runtime backend. It resolves the backend in this order: saved verified endpoint, `runtime-endpoint.json` bootstrap configuration, LAN discovery on port 8000, then the compiled default (if supplied). This allows a Railway/public backend URL to change without rebuilding the APK.
Bootstrap document: `https://raw.githubusercontent.com/REDLINE-INTERACTIVE-DEV/JARVIS/main/runtime-endpoint.json`.

## Desktop
Set `JARVIS_API` or use the API button. Optional voice adapters are in `desktop/voice.py`; install `desktop/requirements-voice.txt` on a compatible machine.

## Safety
The foundation never executes destructive computer actions. They require explicit confirmation and an OS-specific executor that is not yet installed.

## CI
Every push/pull request runs backend tests and attempts Android, Linux, and Windows desktop builds. The Android artifact is a debug APK, not a signed production release.
