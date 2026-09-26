"""Core reasoning/response interface for JARVIS."""
import os
from pathlib import Path
from typing import Protocol

class Brain(Protocol):
    @property
    def provider(self) -> str: ...
    def respond(self, message: str, memories: list[dict]) -> str: ...

class LocalBrain:
    """Local-first JARVIS brain with optional llama.cpp inference."""
    def __init__(self):
        self.model_path = os.getenv("JARVIS_MODEL_PATH")
        self._llm = None
        if self.model_path and Path(self.model_path).is_file():
            try:
                from llama_cpp import Llama
                self._llm = Llama(model_path=self.model_path, n_ctx=int(os.getenv("JARVIS_CTX", "4096")), verbose=False)
            except Exception:
                self._llm = None

    @property
    def provider(self) -> str:
        return "llama.cpp" if self._llm else "local-foundation"

    def respond(self, message: str, memories: list[dict]) -> str:
        message = message.strip()
        if not message:
            return "Please say something and I'll respond."
        if self._llm:
            context = "\n".join(f"{m['kind']}: {m['content']}" for m in reversed(memories[-8:]))
            prompt = "You are JARVIS, a concise local personal assistant.\nMemory:\n" + context + "\n\nUser: " + message + "\nJARVIS:"
            try:
                result = self._llm(prompt, max_tokens=512, stop=["\nUser:"])
                answer = result["choices"][0]["text"].strip()
                if answer:
                    return answer
            except Exception:
                pass
        return f"Local foundation mode is active. You said: {message}"
