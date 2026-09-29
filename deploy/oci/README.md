# Oracle Cloud deployment for JARVIS

Oracle Cloud is infrastructure only. JARVIS inference remains the configured private GGUF model loaded by llama.cpp.

Architecture: Android/Desktop -> JARVIS API -> llama.cpp -> configured GGUF model.

Use an OCI Ampere A1 Always Free VM when available. Oracle documents a total Always Free A1 allocation of 4 OCPUs and 24 GB RAM.

Do not automatically download an AI model. The project owner explicitly supplies the GGUF file.

Configuration:
- JARVIS_MODEL_PATH=/data/jarvis-model.gguf
- JARVIS_DB_PATH=/data/jarvis.db

Deployment:
1. Create an Always Free eligible Ubuntu ARM64 VM in OCI.
2. Attach persistent storage for the selected GGUF and JARVIS data.
3. Install Docker.
4. Clone this repository.
5. Put the selected GGUF at /data/jarvis-model.gguf.
6. Build and run the repository image.
7. Expose only the required JARVIS API port.
8. Verify /health before connecting clients.

Brain isolation: no OpenAI, Gemini, Claude, Grok, or other hosted AI inference provider is configured here. llama.cpp loads the explicitly configured GGUF file.

Never commit GGUF files, credentials, SSH private keys, JWT secrets, or databases. Keep physical device and robot actions authenticated, capability-scoped, and behind the existing safety layer.
