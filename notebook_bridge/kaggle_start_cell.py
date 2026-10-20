"""Single-cell launcher for the already-loaded JARVIS Kaggle brain.

Run this file's contents in the Kaggle notebook after model and processor have
loaded. It does not download or substitute another model.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

EXPECTED_BRAIN = "gemma-4-e4b-it-kaggle"
REPO_URL = "https://github.com/REDLINE-INTERACTIVE-DEV/JARVIS.git"
REPO_DIR = Path("/kaggle/working/JARVIS-bridge")
BRANCH = "main"
API_HOST = "127.0.0.1"
API_PORT = 8000
API_BASE = f"http://{API_HOST}:{API_PORT}"
CLOUDFLARED_PATH = Path("/kaggle/working/cloudflared")
TUNNEL_LOG_PATH = Path("/kaggle/working/cloudflared.log")


def _stop_previous_bridge() -> None:
    for name in ("jarvis_server", "server"):
        instance = globals().get(name)
        if instance is not None and hasattr(instance, "should_exit"):
            instance.should_exit = True
    for name in ("jarvis_server_thread", "server_thread"):
        thread = globals().get(name)
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
    for name in ("jarvis_cloudflared", "cloudflared"):
        process = globals().get(name)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    old_log = globals().get("jarvis_tunnel_log") or globals().get("tunnel_log")
    if old_log is not None and not old_log.closed:
        old_log.close()


if "model" not in globals() or "processor" not in globals():
    raise RuntimeError(
        "Load the JARVIS Gemma model and its processor first; expected variables named model and processor."
    )
if not hasattr(model, "generate") or not hasattr(processor, "apply_chat_template"):
    raise RuntimeError("The current model/processor do not expose the expected Transformers inference interface.")

# Install only bridge server dependencies; do not install another AI model.
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check",
     "fastapi", "uvicorn", "httpx"],
    check=True,
)

_stop_previous_bridge()

if not (REPO_DIR / ".git").is_dir():
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", BRANCH, REPO_URL, str(REPO_DIR)],
        check=True,
    )
else:
    dirty = subprocess.run(
        ["git", "-C", str(REPO_DIR), "status", "--porcelain"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        raise RuntimeError(
            f"{REPO_DIR} has local edits. Preserve them before refreshing the bridge checkout."
        )
    subprocess.run(
        ["git", "-C", str(REPO_DIR), "fetch", "--depth", "1", "origin", BRANCH],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(REPO_DIR), "checkout", "-B", BRANCH, f"origin/{BRANCH}"],
        check=True,
    )

if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

# Force imports to come from the refreshed repository checkout.
sys.modules.pop("notebook_bridge.serve_jarvis", None)
sys.modules.pop("notebook_bridge", None)
import uvicorn
from notebook_bridge.serve_jarvis import create_kaggle_app

JARVIS_API_TOKEN = __import__("secrets").token_urlsafe(32)
app = create_kaggle_app(model, processor, JARVIS_API_TOKEN)
if getattr(app.state.jarvis_brain, "provider", "") != EXPECTED_BRAIN:
    raise RuntimeError("The bridge did not bind the expected Kaggle Gemma brain.")

print("Running JARVIS model-generation smoke test...")
smoke_answer = app.state.jarvis_brain.respond(
    "Reply exactly: JARVIS inference check passed.",
    [],
)
if (
    not isinstance(smoke_answer, str)
    or not smoke_answer.strip()
    or "wasn't able to form a useful response" in smoke_answer.lower()
):
    raise RuntimeError("The loaded JARVIS brain did not pass the generation smoke test.")
print("Model-generation smoke test: PASS")

jarvis_server = uvicorn.Server(
    uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="warning", access_log=False)
)
jarvis_server_thread = threading.Thread(target=jarvis_server.run, name="jarvis-api", daemon=True)
jarvis_server_thread.start()

local_health = None
for _ in range(45):
    try:
        with urllib.request.urlopen(f"{API_BASE}/health", timeout=2) as response:
            local_health = json.loads(response.read().decode("utf-8"))
        if local_health.get("status") == "ok" and local_health.get("brain") == EXPECTED_BRAIN:
            break
    except Exception:
        time.sleep(1)
else:
    jarvis_server.should_exit = True
    raise RuntimeError("JARVIS API did not become healthy on localhost:8000; inspect the notebook logs.")

if not CLOUDFLARED_PATH.is_file():
    subprocess.run(
        ["wget", "-q", "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
         "-O", str(CLOUDFLARED_PATH)],
        check=True,
    )
    CLOUDFLARED_PATH.chmod(0o755)

CLOUDFLARED_PATH.chmod(0o755)
jarvis_tunnel_log = open(TUNNEL_LOG_PATH, "w", encoding="utf-8")
jarvis_cloudflared = subprocess.Popen(
    [str(CLOUDFLARED_PATH), "tunnel", "--no-autoupdate", "--url", API_BASE],
    stdout=jarvis_tunnel_log,
    stderr=subprocess.STDOUT,
)

JARVIS_TUNNEL_URL = None
for _ in range(60):
    time.sleep(1)
    try:
        log_text = TUNNEL_LOG_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log_text = ""
    match = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", log_text)
    if match:
        JARVIS_TUNNEL_URL = match.group(0)
        break
    if jarvis_cloudflared.poll() is not None:
        break

if not JARVIS_TUNNEL_URL:
    jarvis_cloudflared.terminate()
    raise RuntimeError(f"Cloudflare tunnel did not start. Inspect {TUNNEL_LOG_PATH}.")

# Verify public health and token-protected brain identity before printing credentials.
verified = False
for _ in range(30):
    try:
        with urllib.request.urlopen(f"{JARVIS_TUNNEL_URL}/health", timeout=8) as response:
            remote_health = json.loads(response.read().decode("utf-8"))
        auth_request = urllib.request.Request(
            f"{JARVIS_TUNNEL_URL}/auth/check",
            headers={"Accept": "application/json", "X-JARVIS-Token": JARVIS_API_TOKEN},
            method="GET",
        )
        with urllib.request.urlopen(auth_request, timeout=8) as response:
            auth_result = json.loads(response.read().decode("utf-8"))
        if (
            remote_health.get("brain") == EXPECTED_BRAIN
            and auth_result.get("authenticated") is True
            and auth_result.get("brain") == EXPECTED_BRAIN
        ):
            verified = True
            break
    except Exception:
        time.sleep(1)

if not verified:
    jarvis_cloudflared.terminate()
    raise RuntimeError(
        "The public tunnel did not pass the protected brain check. Do not enter an unverified URL; inspect the tunnel log."
    )

print("JARVIS bridge verified: PASS")
print("Active brain:", EXPECTED_BRAIN)
print("Repository revision:", subprocess.run(
    ["git", "-C", str(REPO_DIR), "rev-parse", "--short", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip())
print("HTTPS backend URL (paste into JARVIS > Connection):", JARVIS_TUNNEL_URL)
print("PRIVATE ACCESS TOKEN (paste only into JARVIS > Connection; do not share):")
print(JARVIS_API_TOKEN)
print("Keep this Kaggle session, API server, and tunnel running. Clear notebook outputs before sharing.")
