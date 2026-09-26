import json
import os
import tkinter as tk
from tkinter import messagebox
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DEFAULT_API = os.getenv("JARVIS_API", "http://127.0.0.1:8000")

class JarvisClient:
    def __init__(self, base_url: str = DEFAULT_API):
        self.base_url = base_url.rstrip("/")
    def chat(self, message: str) -> str:
        payload = json.dumps({"message": message}).encode("utf-8")
        request = Request(f"{self.base_url}/chat", data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))["response"]

class JarvisDesktop:
    def __init__(self, root: tk.Tk):
        self.root, self.client = root, JarvisClient()
        root.title("JARVIS"); root.geometry("760x560")
        self.output = tk.Text(root, state="disabled", wrap="word"); self.output.pack(fill="both", expand=True, padx=12, pady=12)
        bottom = tk.Frame(root); bottom.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(bottom); self.entry.pack(side="left", fill="x", expand=True); self.entry.bind("<Return>", lambda _: self.send())
        tk.Button(bottom, text="Send", command=self.send).pack(side="left", padx=(8, 0))
        tk.Button(bottom, text="API", command=self.configure_api).pack(side="left", padx=(8, 0))
        self.write("JARVIS desktop client ready.")

    def write(self, text: str):
        self.output.configure(state="normal"); self.output.insert("end", text + "\n"); self.output.configure(state="disabled"); self.output.see("end")

    def send(self):
        message = self.entry.get().strip()
        if not message: return
        self.entry.delete(0, "end"); self.write("You: " + message)
        try: self.write("JARVIS: " + self.client.chat(message))
        except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as error: self.write("JARVIS: API error: " + str(error))

    def configure_api(self):
        dialog = tk.Toplevel(self.root); dialog.title("JARVIS API"); dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text="API endpoint").pack(padx=12, pady=(12, 4))
        value = tk.Entry(dialog, width=48); value.insert(0, self.client.base_url); value.pack(padx=12, pady=4)
        def save():
            endpoint = value.get().strip().rstrip("/")
            if not endpoint.startswith(("http://", "https://")):
                messagebox.showerror("Invalid endpoint", "Use an http:// or https:// endpoint."); return
            self.client.base_url = endpoint; dialog.destroy()
        tk.Button(dialog, text="Save", command=save).pack(pady=12)

if __name__ == "__main__":
    root = tk.Tk(); JarvisDesktop(root); root.mainloop()
