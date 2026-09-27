# JARVIS function map

One clearly named facade file now represents each major capability under `backend/functions/`.

Brain · Memory · VoiceInput · VoiceOutput · Reasoning · Research · Tasks · Tools · Missions · Screen · Robots · Service · Sync.

These facades avoid duplicating implementation code. The tested `backend/app/...` packages remain the source of truth, while this layer gives the project the named functional organization you requested.

Platform-specific voice input/output stays in the Android and desktop clients; the backend facade exposes the shared voice-state contract.
