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
    IDENTITY = (
        "You are JARVIS, an independent personal AI companion and task orchestrator. "
        "Speak naturally and never invent actions, memories, or tool results."
    )
    def __init__(self) -> None:
        self.model_path = os.getenv("JARVIS_MODEL_PATH")
        self._llm = None
        if self.model_path and Path(self.model_path).is_file():
            try:
                from llama_cpp import Llama
                self._llm = Llama(model_path=self.model_path, n_ctx=self._context_size(), verbose=False)
            except Exception:
                self._llm = None
    @staticmethod
    def _context_size() -> int:
        try: value = int(os.getenv("JARVIS_CTX", "8192"))
        except ValueError: value = 8192
        return max(512, min(value, 32768))
    @property
    def provider(self) -> str:
        return "llama.cpp" if self._llm is not None else "local-foundation"
    @staticmethod
    def _memory_context(memories: list[dict[str, Any]]) -> str:
        recent = list(reversed(memories[:40]))
        return "\n".join(f"{x.get('kind','memory')}: {x.get('content','')}" for x in recent if x.get("content"))
    def _build_prompt(self, message: str, memories: list[dict[str, Any]]) -> str:
        return f"{self.IDENTITY}\n\nMemory:\n{self._memory_context(memories) or '(none)'}\n\nUser: {message}\nJARVIS:"
    def respond(self, message: str, memories: list[dict[str, Any]]) -> str:
        message = message.strip()
        if not message:
            return "Please say something and I'll respond."
        if self._llm is not None:
            try:
                result = self._llm(self._build_prompt(message, memories), max_tokens=700, stop=["\nUser:", "\nJARVIS:"])
                choices = result.get("choices", [])
                answer = choices[0].get("text", "").strip() if choices else ""
                if answer: return answer
            except Exception:
                pass
        return f"JARVIS local foundation mode is active. You said: {message}"
    def answer_with_research(self, message: str, memories: list[dict[str, Any]], results: list[dict[str, str]]) -> str:
        if not results: return "I searched the web, but I couldn't find usable results."
        if self._llm is None:
            return "I found these results:\n" + "\n".join(f"{i+1}. {x['title']} — {x['url']}" for i, x in enumerate(results))
        context = "\n".join(f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results)
        prompt = f"{self.IDENTITY}\nUse only supplied search results for current claims.\nMemory:\n{self._memory_context(memories)}\nUser: {message}\nResults:\n{context}\nJARVIS:"
        try:
            result = self._llm(prompt, max_tokens=900, stop=["\nUser:", "\nJARVIS:"])
            choices = result.get("choices", [])
            answer = choices[0].get("text", "").strip() if choices else ""
            if answer: return answer
        except Exception:
            pass
        return "I found the research, but I couldn't summarize it locally."
