# JARVIS Gemma brain connection

This is the current Gemma-backed JARVIS inference bridge. It connects the **already-loaded** Gemma 4 E4B model in the Kaggle notebook to JARVIS's existing FastAPI, memory, research, task, device, and Android API surfaces. It does not contain model weights or credentials. Gemma is the active brain for this implementation, not a reduced or experimental feature mode.

## Important limits

- Kaggle sessions are temporary. The app reaches the active Gemma brain while the notebook, model, API server, and tunnel are running.
- The public tunnel URL changes when recreated. The access token must stay private.
- Never commit the tunnel URL plus token, the token itself, notebook output containing the token, or model weights.
- The free Kaggle runtime is session-bound and can stop or change its public tunnel URL; that hosting limitation does not restrict the JARVIS feature roadmap. Keep the model server and tunnel running while using the app.

## Notebook steps

Run these cells **after the model has loaded successfully** in `JARVIS_Pretrained_Brain`.

### 1. Install only the API-server dependencies

```python
%pip install -q fastapi uvicorn httpx
```

Do not install the repository's full `backend/requirements.txt` in this Python 3.13 notebook: it includes `llama-cpp-python`, which failed to install in this environment.

### 2. Get the bridge code from this repository branch

Use the feature branch while the pull request is under review. After it is merged, change `--branch fix/gemma-production-connection` to `--branch main`.

```python
import os, sys, subprocess

repo_dir = "/kaggle/working/JARVIS"
if not os.path.isdir(repo_dir):
    subprocess.run([
        "git", "clone", "--depth", "1",
        "--branch", "feat/kaggle-gemma-bridge",
        "https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS.git",
        repo_dir,
    ], check=True)
if repo_dir not in sys.path:
    sys.path.insert(0, repo_dir)
```

### 3. Start the JARVIS API using the model already in memory

```python
import secrets
import threading
import uvicorn
from notebook_bridge.serve_jarvis import create_kaggle_app

JARVIS_API_TOKEN = secrets.token_urlsafe(32)
app = create_kaggle_app(model, processor, JARVIS_API_TOKEN)

server = uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
)
server_thread = threading.Thread(target=server.run, daemon=True)
server_thread.start()

print("JARVIS API starting. Keep this notebook session alive.")
print("PRIVATE ACCESS TOKEN (copy only into your JARVIS app; do not share):")
print(JARVIS_API_TOKEN)
```

### 4. Create a temporary HTTPS tunnel

```python
import os, re, subprocess, time

cloudflared_path = "/kaggle/working/cloudflared"
if not os.path.isfile(cloudflared_path):
    subprocess.run([
        "wget", "-q",
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        "-O", cloudflared_path,
    ], check=True)
    os.chmod(cloudflared_path, 0o755)

tunnel_log = open("/kaggle/working/cloudflared.log", "w")
cloudflared = subprocess.Popen(
    [cloudflared_path, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000"],
    stdout=tunnel_log,
    stderr=subprocess.STDOUT,
)
tunnel_url = None
for _ in range(40):
    time.sleep(1)
    with open("/kaggle/working/cloudflared.log", "r") as log_file:
        match = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", log_file.read())
    if match:
        tunnel_url = match.group(0)
        break

if not tunnel_url:
    raise RuntimeError("Tunnel URL not found. Inspect /kaggle/working/cloudflared.log.")
print("Temporary JARVIS HTTPS URL:", tunnel_url)
print("Health check:", tunnel_url + "/health")
```

Open the printed `/health` URL in a browser. It should return JSON with `"status":"ok"` and `"brain":"gemma-4-e4b-it-kaggle"`. The `/health` route is intentionally public; every other API route requires the private token.

### 5. Connect the Android app

Install the Android APK built from this feature branch's GitHub Actions workflow. In the app, tap **Connection** and enter:

- **HTTPS backend URL:** the temporary `https://....trycloudflare.com` URL (no `/chat` suffix).
- **Private access token:** the token printed in step 3.

Tap **Save**. The app verifies that `/health` reports the loaded `gemma-4-e4b-it-kaggle` brain, then sends chat and voice requests with the private `X-JARVIS-Token` header. Android encrypts the token with Android Keystore-backed AES-GCM storage.

## What you must do

1. Keep the Kaggle notebook session running.
2. Keep the API server and Cloudflare tunnel processes alive.
3. Enter the current tunnel URL and token in the Android app each time a new tunnel/token is created.
4. Stop sharing the notebook output: it contains a private token. Regenerate the token and reconnect if it is exposed.
5. If the Kaggle session ends, restart the model/API/tunnel; this is not 24/7 hosting.
