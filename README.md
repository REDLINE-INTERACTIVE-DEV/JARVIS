# JARVIS — Your local-first personal AI

JARVIS is a standalone personal assistant with a local-first foundation.

## Current foundation
- FastAPI backend with persistent SQLite memory
- Optional local GGUF brain through llama.cpp
- Structured tool registry with destructive-action confirmation gates
- Task engine with explicit planning/confirmation/execution/completion states
- Android Jetpack Compose client with typed chat, configurable API endpoint and speech input
- Android TextToSpeech output support
- Lightweight desktop client with configurable API endpoint
- Optional desktop STT/TTS adapters
- Backend pytest suite with isolated temporary databases
- GitHub Actions for backend tests, Android APK, and Linux/Windows desktop packages

## Run backend
```bash
python -m pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Optional local brain
Install `backend/requirements-llama.txt`, provide a compatible GGUF model, and set `JARVIS_MODEL_PATH=/path/to/model.gguf`.

## Android
Emulator default: `http://10.0.2.2:8000`. On a physical phone, set the API endpoint in the app to the backend machine's LAN address.

## Desktop
Set `JARVIS_API` or use the API button. Optional voice adapters are in `desktop/voice.py`; install `desktop/requirements-voice.txt` on a compatible machine.

## Safety
The foundation never executes destructive computer actions. They require explicit confirmation and an OS-specific executor that is not yet installed.

## CI
Every push/pull request runs backend tests and attempts Android, Linux desktop, and Windows desktop builds. The Android artifact is a debug APK, not a signed production release.
