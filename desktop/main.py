import json
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API = os.getenv("JARVIS_API", "http://127.0.0.1:8000")

class JarvisClient:
    def __init__(self, base_url: str = DEFAULT_API):
        self.base_url = base_url.rstrip("/")

    def health(self) -> bool:
        try:
            with urlopen(Request(f"{self.base_url}/health", headers={"Accept": "application/json"}), timeout=5) as response:
                return 200 <= response.status < 300
        except (HTTPError, URLError, TimeoutError, OSError):
            return False

    def chat(self, message: str) -> str:
        payload = json.dumps({"message": message}).encode("utf-8")
        request = Request(f"{self.base_url}/chat", data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        last = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=60) as response:
                    return json.loads(response.read().decode("utf-8"))["response"]
            except (HTTPError, URLError, TimeoutError, OSError, KeyError, json.JSONDecodeError) as error:
                last = error
                if attempt < 2: time.sleep(0.5 * (attempt + 1))
        raise last

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

    def monitor_connection(self):
        def worker():
            online = self.client.health()
            self.root.after(0, lambda: self.set_connection(online))
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(10_000, self.monitor_connection)

    def set_connection(self, online: bool):
        self.online = online
        self.status.configure(text="● ONLINE" if online else "○ OFFLINE")

    def write(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text + "
")
        self.output.configure(state="disabled")
        self.output.see("end")

    def send(self, message: str | None = None):
        message = (message if message is not None else self.entry.get()).strip()
        if not message: return
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
        except Exception as error: self.write("Voice: " + str(error))

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
        tk.Label(dialog, text="API endpoint").pack(padx=12, pady=(12, 4))
        value = tk.Entry(dialog, width=48)
        value.insert(0, self.client.base_url)
        value.pack(padx=12, pady=4)
        def save():
            endpoint = value.get().strip().rstrip("/")
            if not endpoint.startswith(("http://", "https://")):
                messagebox.showerror("Invalid endpoint", "Use an http:// or https:// endpoint.")
                return
            self.client.base_url = endpoint
            dialog.destroy()
        tk.Button(dialog, text="Save", command=save).pack(pady=12)

if __name__ == "__main__":
    root = tk.Tk()
    JarvisDesktop(root)
    root.mainloop()
