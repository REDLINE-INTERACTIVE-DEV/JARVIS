# JARVIS — Your private local-first personal AI

JARVIS is a standalone personal assistant designed around a private local language-model brain and a cinematic, proactive assistant experience.

## Brain architecture
JARVIS does not use OpenAI, Claude, Grok, Gemini, or another hosted AI service as its brain.
Production inference is: Android/Desktop → your JARVIS backend → llama.cpp → your private GGUF model.
The model runs inside infrastructure you control. API keys and secrets are never embedded in the Android APK or committed to this repository.
Ordinary non-AI services may still be used for web research, hosting, or delivery. They are not JARVIS's brain.

## Cinematic target
The target is an original assistant with calm polished British-style manner, concise answers, understated humour, persistent private memory, proactive planning, research, computer/device/tool orchestration, visible listening/thinking/speaking states, voice, typed chat, wake phrase support, and screen/device/robot expansion points.
It does not reproduce movie dialogue or clone a film performer's exact voice. The goal is the feel and capability pattern.

## Local brain setup
Install the llama.cpp Python binding:
python -m pip install -r backend/requirements-llama.txt
Place a compatible instruct GGUF model on your private machine and set:
JARVIS_MODEL_PATH=/private/path/to/model.gguf
Optional tuning: JARVIS_CTX, JARVIS_THREADS, JARVIS_GPU_LAYERS.
Without a model, the service deliberately reports foundation state rather than pretending it has a full generative brain.

## Run backend
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

## Android
The Android client does not use 127.0.0.1, localhost, or emulator-only 10.0.2.2 as its runtime backend. It resolves the backend from saved configuration, bootstrap configuration, LAN discovery, then compiled default if supplied.

## Voice
Android speech recognition and device TextToSpeech are used. The exact movie voice/performance is not reproduced; a generic calm British-style profile is used instead.

## Safety
Destructive computer actions require explicit confirmation. Physical robot control remains behind a safety/authorization layer.

## CI
Every push/pull request runs backend tests and attempts Android, Linux and Windows builds. The Android artifact is a debug APK, not a signed production release.
