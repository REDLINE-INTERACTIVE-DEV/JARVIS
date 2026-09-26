"""Core reasoning/response interface for JARVIS."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol


class Brain(Protocol):
    @property
    def provider(self) -> str: ...

    def respond(self, message: str, memories: list[dict[str, Any]]) -> str: ...


class LocalBrain:
    """Local-first JARVIS brain with optional llama.cpp inference."""

    def __init__(self) -> None:
        self.model_path = os.getenv("JARVIS_MODEL_PATH")
        self._llm = None

        if self.model_path and Path(self.model_path).is_file():
            try:
                from llama_cpp import Llama

                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self._context_size(),
                    verbose=False,
                )
            except Exception:
                self._llm = None

    @staticmethod
    def _context_size() -> int:
        try:
            value = int(os.getenv("JARVIS_CTX", "4096"))
        except ValueError:
            value = 4096
        return max(512, min(value, 32768))

    @property
    def provider(self) -> str:
        return "llama.cpp" if self._llm is not None else "local-foundation"

    @staticmethod
    def _memory_context(memories: list[dict[str, Any]]) -> str:
        recent = memories[-8:]
        return "\n".join(
            f"{item.get('kind', 'memory')}: {item.get('content', '')}"
            for item in recent
            if item.get("content")
        )

    def respond(self, message: str, memories: list[dict[str, Any]]) -> str:
        message = message.strip()
        if not message:
            return "Please say something and I'll respond."

        if self._llm is not None:
            context = self._memory_context(memories)
            prompt = (
                "You are JARVIS, a concise local personal AI assistant. "
                "Use the supplied memory only as context; do not invent facts.\n\n"
                f"Memory:\n{context or '(none)'}\n\n"
                f"User: {message}\n"
                "JARVIS:"
            )
            try:
                result = self._llm(
                    prompt,
                    max_tokens=512,
                    stop=["\nUser:", "\nJARVIS:"],
                )
                choices = result.get("choices", [])
                answer = choices[0].get("text", "").strip() if choices else ""
                if answer:
                    return answer
            except Exception:
                pass

        return f"Local foundation mode is active. You said: {message}"
