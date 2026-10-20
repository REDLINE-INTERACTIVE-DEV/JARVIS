import ipaddress
import json
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

KEYRING_SERVICE = "JARVIS"
KEYRING_USERNAME = "api_token"
EXPECTED_BRAIN = "gemma-4-e4b-it-kaggle"
CONFIG_PATH = Path(os.getenv("APPDATA") or (Path.home() / ".config")) / "JARVIS" / "desktop.json"


def is_public_https_endpoint(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False
        if parsed.path not in ("", "/"):
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass
        _ = parsed.port
        return True
    except ValueError:
        return False


def load_saved_endpoint() -> str:
    try:
        endpoint = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("endpoint", "")
    except (OSError, ValueError, AttributeError):
        return ""
    return endpoint.rstrip("/") if isinstance(endpoint, str) and is_public_https_endpoint(endpoint) else ""


def save_endpoint_config(endpoint: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"endpoint": endpoint}, indent=2), encoding="utf-8")


def load_saved_token() -> str:
    environment_token = os.getenv("JARVIS_API_TOKEN", "").strip()
    if len(environment_token) >= 32:
        return environment_token
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or ""
    except Exception:
        return ""


def save_token_secure(token: str) -> bool:
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) == token
    except Exception:
        return False


DEFAULT_API = os.getenv("JARVIS_API", load_saved_endpoint()).strip().rstrip("/")
if not is_public_https_endpoint(DEFAULT_API):
    DEFAULT_API = ""


class JarvisClient:
    def __init__(self, base_url: str = DEFAULT_API, api_token: str | None = None):
        self.base_url = base_url.rstrip("/") if is_public_https_endpoint(base_url) else ""
        self.api_token = (api_token if api_token is not None else load_saved_token()).strip()

    def health(self) -> bool:
        if not is_public_https_endpoint(self.base_url) or len(self.api_token) < 32:
            return False
        request = Request(
            f"{self.base_url}/auth/check",
            headers={"Accept": "application/json", "X-JARVIS-Token": self.api_token},
        )
        try:
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return (
                    200 <= response.status < 300
                    and payload.get("authenticated") is True
                    and payload.get("brain") == EXPECTED_BRAIN
                )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
            return False

    def chat(self, message: str) -> str:
        if not is_public_https_endpoint(self.base_url):
            raise URLError("Configure a valid public HTTPS JARVIS endpoint.")
        if len(self.api_token) < 32:
            raise URLError("Configure the private JARVIS API token in the API settings.")
        payload = json.dumps({"message": message}).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-JARVIS-Token": self.api_token,
            },
            method="POST",
        )
        last = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    answer = result.get("response")
                    if not isinstance(answer, str):
                        raise ValueError("JARVIS API response did not contain a text response.")
                    return answer
            except HTTPError as error:
                if error.code in (401, 403):
                    raise
                last = error
            except (URLError, TimeoutError, OSError, ValueError, TypeError) as error:
                last = error
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
        raise last or URLError("JARVIS API request failed.")

class JarvisDesktop:
    def __init__(self, root: tk.Tk):
        self.root, self.client = root, JarvisClient()
        self.listening = False
        self.online = False
        root.title("JARVIS")
        self.status = tk.Label(root, text="○ OFFLINE")
        self.status.pack(anchor="e", padx=12, pady=(8, 0))
        root.geometry("760x700")

        self.core = tk.Canvas(root, height=190, highlightthickness=0)
        self.core.pack(fill="x", padx=12, pady=(12, 0))
        self.output = tk.Text(root, state="disabled", wrap="word")
        self.output.pack(fill="both", expand=True, padx=12, pady=12)

        bottom = tk.Frame(root)
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _: self.send())
        tk.Button(bottom, text="Send", command=self.send).pack(side="left", padx=(8, 0))
        tk.Button(bottom, text="Voice", command=self.voice).pack(side="left", padx=(8, 0))
        tk.Button(bottom, text="API", command=self.configure_api).pack(side="left", padx=(8, 0))
        self.write("JARVIS desktop client ready.")
        self.draw_core()
        self.monitor_connection()

    def check_connection_now(self):
        def worker():
            online = self.client.health()
            self.root.after(0, lambda: self.set_connection(online))
        threading.Thread(target=worker, daemon=True).start()

    def monitor_connection(self):
        self.check_connection_now()
        self.root.after(10_000, self.monitor_connection)

    def set_connection(self, online: bool):
        self.online = online
        self.status.configure(text="● ONLINE" if online else "○ OFFLINE")

    def write(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.configure(state="disabled")
        self.output.see("end")

    def send(self, message: str | None = None):
        message = (message if message is not None else self.entry.get()).strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self.write("You: " + message)

        def worker():
            try:
                answer = self.client.chat(message)
                self.root.after(0, lambda: self.write("JARVIS: " + answer))
                self.root.after(0, lambda: self.set_connection(True))
                try:
                    from desktop.voice import speak
                    self.root.after(0, lambda: speak(answer))
                except Exception as error:
                    self.root.after(0, lambda: self.write("Voice: " + str(error)))
            except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError) as error:
                self.root.after(0, lambda: (self.set_connection(False), self.write("JARVIS: API error: " + str(error))))

        threading.Thread(target=worker, daemon=True).start()

    def voice(self):
        try:
            from desktop.voice import listen
            self.write("Listening...")
            threading.Thread(target=self._voice_worker, args=(listen,), daemon=True).start()
        except Exception as error:
            self.write("Voice: " + str(error))

    def _voice_worker(self, listen):
        try:
            text = listen()
            self.root.after(0, lambda: self.send(text))
        except Exception as error:
            self.root.after(0, lambda: self.write("Voice: " + str(error)))

    def draw_core(self):
        import math
        self.core.delete("all")
        width = max(self.core.winfo_width(), 760)
        center_x, center_y = width / 2, 95
        radius = 42
        self.core.create_oval(center_x-radius, center_y-radius, center_x+radius, center_y+radius, outline="#4ab3ff", width=3)
        for i in range(64):
            angle = i * math.tau / 64
            wave = 1 + 0.18 * math.sin(i * 0.7 + time.monotonic() * 2)
            inner = radius * 1.35
            outer = inner + 16 * wave
            self.core.create_line(center_x+math.cos(angle)*inner, center_y+math.sin(angle)*inner, center_x+math.cos(angle)*outer, center_y+math.sin(angle)*outer, fill="#4ab3ff", width=2)
        self.root.after(80, self.draw_core)

    def configure_api(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("JARVIS API")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Public HTTPS API endpoint").pack(padx=12, pady=(12, 4))
        endpoint_entry = tk.Entry(dialog, width=52)
        endpoint_entry.insert(0, self.client.base_url)
        endpoint_entry.pack(padx=12, pady=4)

        tk.Label(dialog, text="Private API token (masked; stored in OS credential store when available)").pack(
            padx=12, pady=(8, 4)
        )
        token_entry = tk.Entry(dialog, width=52, show="*")
        token_entry.insert(0, self.client.api_token)
        token_entry.pack(padx=12, pady=4)

        def save():
            endpoint = endpoint_entry.get().strip().rstrip("/")
            token = token_entry.get().strip()
            if not is_public_https_endpoint(endpoint):
                messagebox.showerror(
                    "Invalid endpoint",
                    "Enter a public HTTPS base URL only (no /chat suffix, localhost, or HTTP URL).",
                    parent=dialog,
                )
                return
            if len(token) < 32:
                messagebox.showerror(
                    "Invalid token",
                    "The private JARVIS access token must be at least 32 characters.",
                    parent=dialog,
                )
                return

            self.client.base_url = endpoint
            self.client.api_token = token
            try:
                save_endpoint_config(endpoint)
            except OSError:
                messagebox.showwarning(
                    "Endpoint not saved",
                    "The endpoint is active for this session but could not be saved to the local config file.",
                    parent=dialog,
                )

            if not save_token_secure(token):
                messagebox.showwarning(
                    "Token storage unavailable",
                    "JARVIS will use this token for the current session only. On Windows, the token is normally saved in the OS credential store; do not put it in a public file.",
                    parent=dialog,
                )
            dialog.destroy()
            self.check_connection_now()

        tk.Button(dialog, text="Save", command=save).pack(pady=12)

if __name__ == "__main__":
    root = tk.Tk()
    JarvisDesktop(root)
    root.mainloop()
