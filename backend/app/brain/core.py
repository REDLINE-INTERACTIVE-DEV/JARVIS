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
    """Independent local-first JARVIS personality and response brain."""

    IDENTITY = (
        "You are JARVIS, an independent personal AI companion and task orchestrator. "
        "Speak naturally like a capable long-term companion, not like a generic command parser. "
        "Be calm, witty when appropriate, concise when the situation is simple, and detailed when "
        "the user needs reasoning. Keep conversational context and use supplied memory only as facts. "
        "Never invent personal history, completed actions, or tool results. Distinguish conversation, "
        "reasoning, research, and tool execution. When a request contains multiple independent goals, "
        "keep every goal tracked and do not silently drop one. Ask for clarification only when it is "
        "genuinely required."
    )

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
            value = int(os.getenv("JARVIS_CTX", "8192"))
        except ValueError:
            value = 8192
        return max(512, min(value, 32768))

    @property
    def provider(self) -> str:
        return "llama.cpp" if self._llm is not None else "local-foundation"

    @staticmethod
    def _memory_context(memories: list[dict[str, Any]]) -> str:
        # MemoryStore returns newest-first. Feed the newest bounded window
        # chronologically so the model sees the conversation in the right order.
        recent = list(reversed(memories[:40]))
        return "\n".join(
            f"{item.get('kind', 'memory')}: {item.get('content', '')}"
            for item in recent
            if item.get("content")
        )

    def _build_prompt(self, message: str, memories: list[dict[str, Any]]) -> str:
        context = self._memory_context(memories)
        return (
            f"{self.IDENTITY}\n\n"
            f"Relevant long-term memory and recent conversation:\n"
            f"{context or '(none)'}\n\n"
            f"User: {message}\nJARVIS:"
        )

    def respond(self, message: str, memories: list[dict[str, Any]]) -> str:
        message = message.strip()
        if not message:
            return "Please say something and I'll respond."
        if self._llm is not None:
            try:
                result = self._llm(
                    self._build_prompt(message, memories),
                    max_tokens=700,
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
            f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results
        )
        memory = self._memory_context(memories)
        if self._llm is None:
            return (
                "I found these results:\n"
                + "\n".join(
                    f"{i + 1}. {x['title']} — {x['url']}"
                    for i, x in enumerate(results)
                )
            )
        prompt = (
            f"{self.IDENTITY}\n\n"
            f"Use ONLY the supplied web results for current factual claims. "
            f"Separate sourced facts from reasoning and mention relevant source URLs. "
            f"Use conversation memory for continuity without inventing facts.\n\n"
            f"Memory:\n{memory or '(none)'}\n\n"
            f"User: {message}\n\nSearch results:\n{context}\n\nJARVIS:"
        )
        try:
            result = self._llm(
                prompt,
                max_tokens=900,
                stop=["\nUser:", "\nJARVIS:"],
            )
            choices = result.get("choices", [])
            answer = choices[0].get("text", "").strip() if choices else ""
            if answer:
                return answer
        except Exception:
            pass
        return "I found search results, but I couldn't summarize them locally."
