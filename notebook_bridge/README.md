# JARVIS Kaggle Gemma brain bridge

This bridge connects the already-loaded Gemma 4 E4B model in the Kaggle notebook to the existing JARVIS API and Android app. It contains no model weights or credentials.

## Hosting and security limits

- Kaggle sessions are temporary. JARVIS is reachable only while the notebook, model, API server, and tunnel are running.
- The temporary HTTPS tunnel URL changes when recreated. Keep the access token private.
- Never commit the tunnel URL plus token, the token itself, notebook output containing the token, or model weights.
- The endpoint is for a personal demonstration, not permanent hosting. A Kaggle session ending is a hosting limitation.
- Android stores the access token encrypted with an AES key held by Android Keystore. The app validates the protected `/auth/check` endpoint before reporting the brain as connected.

## Fast path: one-cell launcher

After the model finishes loading in **Pre trained model** (yashasvishahi/pre-trained-model), run this single cell. It downloads the current bridge launcher from this repository and executes it in the notebook's existing kernel, using the already-loaded model and processor variables.

**Important:** Kaggle's saved output shows the last run completed; that does not mean the model is still resident in RAM/GPU memory. Start an active notebook session and rerun the model-loading cell(s) so the variables `model` and `processor` exist, then run the launcher. You do not need to retrain the model.

    import urllib.request

    launcher_url = "https://raw.githubusercontent.com/REDLINE-INTERACTIVE-DEV/JARVIS/main/notebook_bridge/kaggle_start_cell.py"
    with urllib.request.urlopen(launcher_url, timeout=30) as response:
        launcher_source = response.read().decode("utf-8")
    exec(compile(launcher_source, "kaggle_start_cell.py", "exec"), globals())

The launcher installs only FastAPI/Uvicorn/HTTPX, refreshes the bridge checkout, runs a real model-generation smoke test, starts the local API and temporary HTTPS tunnel, and verifies both public health and the protected Gemma identity before printing the URL/token. It does not download or substitute another AI model and does not write the URL or token to GitHub. Review the launcher source in this repository if you want to inspect it before running. Choose either this one-cell path or the manual path below, not both in the same kernel; both start the same local API port.

## Alternative: manual notebook setup

Run these cells only after the model and its processor have loaded successfully in your Kaggle notebook **Pre trained model** (`yashasvishahi/pre-trained-model`). The saved run confirms that Gemma loaded on the two Tesla T4 GPUs and completed text-generation checks.

### 1. Install only API-server dependencies

```python
%pip install -q fastapi uvicorn httpx
```

Do not install the full `backend/requirements.txt` into this Python 3.13 notebook: it includes `llama-cpp-python`, which is not required for this already-loaded Transformers model.

### 2. Get the current bridge code

Use `main`; it now contains the bridge, security, and CI fixes.

The code below refreshes an existing clean checkout instead of silently keeping an old branch. It stops rather than overwriting local edits.

```python
import os, subprocess, sys

REPO_URL = "https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS.git"
REPO_DIR = "/kaggle/working/JARVIS-bridge"
BRANCH = "main"

if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", BRANCH, REPO_URL, REPO_DIR],
        check=True,
    )
else:
    dirty = subprocess.run(
        ["git", "-C", REPO_DIR, "status", "--porcelain"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        raise RuntimeError(
            f"{REPO_DIR} has local edits; preserve or remove that folder before refreshing."
        )
    subprocess.run(["git", "-C", REPO_DIR, "fetch", "--depth", "1", "origin", BRANCH], check=True)
    subprocess.run(
        ["git", "-C", REPO_DIR, "checkout", "-B", BRANCH, f"origin/{BRANCH}"],
        check=True,
    )

if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

print("JARVIS bridge revision:", subprocess.run(
    ["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip())
```

### 3. Start the JARVIS API using the model already in memory

```python
import secrets
import threading
import time
import urllib.request
import uvicorn
from notebook_bridge.serve_jarvis import create_kaggle_app

JARVIS_API_TOKEN = secrets.token_urlsafe(32)
app = create_kaggle_app(model, processor, JARVIS_API_TOKEN)

server = uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
)
server_thread = threading.Thread(target=server.run, daemon=True)
server_thread.start()

# Verify the local API is ready before starting the public tunnel.
for attempt in range(30):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
            if response.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("JARVIS API did not become healthy; inspect the notebook logs.")

print("JARVIS API is healthy. Keep this notebook session alive.")
print("PRIVATE ACCESS TOKEN (paste only into the JARVIS app; do not share):")
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

Open the `/health` URL. It should return JSON containing `"status":"ok"` and `"brain":"gemma-4-e4b-it-kaggle"`. Health is public by design; every other route requires the private `X-JARVIS-Token` header.

### 5. Connect the Android app

Install the Android APK from the successful GitHub Actions run for this branch. In JARVIS, open **Connection** and enter:

- **HTTPS backend URL:** the temporary `https://....trycloudflare.com` URL, without a `/chat` suffix.
- **Private access token:** the token printed in step 3.

Tap **Save**. The app verifies the protected `/auth/check` route, then sends typed and voice requests with the private token. Test with a simple message such as `Reply exactly: JARVIS connection verified.`

## Keep it working

1. Keep the Kaggle notebook session, API server, and tunnel alive.
2. Enter the current URL and token in the app whenever a new tunnel/token is created.
3. Clear notebook outputs before sharing the notebook. If the token is exposed, restart the bridge with a newly generated token and reconnect.
4. If the Kaggle session ends, restart the model/API/tunnel. This temporary endpoint is not 24/7 hosting.
5. Do not commit a real endpoint or token to `runtime-endpoint.json`; keep that public bootstrap file empty and use the app's secure Connection settings.
6. SQLite memory is stored at `/kaggle/working/jarvis_memory.db` and is session-scoped. It is not automatically backed up across Kaggle sessions; do not commit personal memory or credentials to the public repository.
