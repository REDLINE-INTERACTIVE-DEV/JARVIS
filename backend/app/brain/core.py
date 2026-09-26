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
                "You are JARVIS, a composed, precise personal AI assistant. "
                "Be helpful, concise, calm, and conversational. "
                "Use memory only as context and never invent facts. "
                "When current web results are supplied, distinguish them from "
                "your own reasoning and cite the supplied source URLs.\n\n"
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

    def answer_with_research(
        self,
        message: str,
        memories: list[dict[str, Any]],
        results: list[dict[str, str]],
    ) -> str:
        if not results:
            return "I searched the web, but I couldn't find usable results."
        context = "\n".join(
            f"- {item['title']} | {item['url']} | {item['snippet']}"
            for item in results
        )
        if self._llm is None:
            return "I found these results:\n" + "\n".join(
                f"{i + 1}. {item['title']} — {item['url']}"
                for i, item in enumerate(results)
            )

        prompt = (
            "You are JARVIS. Answer the user's request using ONLY the supplied "
            "web-search results for current factual claims. Give a concise "
            "summary and mention the relevant source URLs. If the results are "
            "insufficient, say so clearly.\n\n"
            f"User: {message}\n\nSearch results:\n{context}\n\nJARVIS:"
        )
        try:
            result = self._llm(prompt, max_tokens=700, stop=["\nUser:", "\nJARVIS:"])
            choices = result.get("choices", [])
            answer = choices[0].get("text", "").strip() if choices else ""
            if answer:
                return answer
        except Exception:
            pass
        return "I found search results, but I couldn't summarize them locally."
