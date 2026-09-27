"""High-throughput independent JARVIS brain runtime."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .core import LocalBrain
from .fastpath import FastPath
from .multitask import Goal, MultiTaskCoordinator


@dataclass(frozen=True)
class RuntimeStats:
    provider: str
    max_concurrency: int
    requests: int
    failures: int


class BrainRuntime:
    """Route fast work locally and model work through independent parallel slots."""

    def __init__(self, brain: LocalBrain | None = None) -> None:
        self.brain = brain or LocalBrain()
        self.fastpath = FastPath()
        self.coordinator = MultiTaskCoordinator()
        self.url = os.getenv("JARVIS_LLM_URL", "").strip().rstrip("/")
        self.model = os.getenv("JARVIS_LLM_MODEL", "jarvis")
        self.max_concurrency = self._int_env("JARVIS_BRAIN_CONCURRENCY", 8, 1, 64)
        self.timeout = self._int_env("JARVIS_BRAIN_TIMEOUT", 45, 5, 180)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._requests = 0
        self._failures = 0

    @staticmethod
    def _int_env(name: str, default: int, low: int, high: int) -> int:
        try: value = int(os.getenv(name, str(default)))
        except ValueError: value = default
        return max(low, min(value, high))

    @property
    def provider(self) -> str:
        return "llama.cpp-server" if self.url else self.brain.provider

    def stats(self) -> RuntimeStats:
        return RuntimeStats(self.provider, self.max_concurrency, self._requests, self._failures)

    async def respond(self, message: str, memories: list[dict[str, Any]]) -> str:
        message = message.strip()
        fast = self.fastpath.try_answer(message)
        if fast is not None:
            return fast
        async with self._semaphore:
            self._requests += 1
            if self.url:
                try: return await self._server_chat(message, memories)
                except Exception: self._failures += 1
            try: return await asyncio.to_thread(self.brain.respond, message, memories)
            except Exception:
                self._failures += 1
                raise

    async def multitask(self, request: str, memories: list[dict[str, Any]]) -> list[dict[str, str]]:
        goals = self.coordinator.split_goals(request)
        if len(goals) <= 1:
            return [{"goal_id": "1", "goal": request.strip(), "status": "completed", "result": await self.respond(request, memories)}]

        async def worker(goal: Goal) -> str:
            return await self.respond(goal.text, memories)

        return await self.coordinator.run(goals, worker)

    async def answer_with_research(self, message: str, memories: list[dict[str, Any]], results: list[dict[str, str]]) -> str:
        async with self._semaphore:
            if self.url:
                try:
                    context = "\n".join(f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results)
                    prompt = f"{self.brain.IDENTITY}\n\nUse only supplied search results for current facts.\n\nUser: {message}\n\nSearch results:\n{context}"
                    return await self._server_prompt(prompt, 700)
                except Exception: self._failures += 1
            return await asyncio.to_thread(self.brain.answer_with_research, message, memories, results)

    async def _server_chat(self, message: str, memories: list[dict[str, Any]]) -> str:
        memory = "\n".join(f"{x.get('kind', 'memory')}: {x.get('content', '')}" for x in memories[-8:] if x.get("content")) or "(none)"
        prompt = f"{self.brain.IDENTITY}\n\nRelevant memory:\n{memory}\n\nUser: {message}\nJARVIS:"
        return await self._server_prompt(prompt, 512)

    async def _server_prompt(self, prompt: str, max_tokens: int) -> str:
        endpoint = self.url if self.url.endswith("/chat/completions") else self.url + "/v1/chat/completions"
        payload = {"model": self.model, "messages": [{"role": "system", "content": self.brain.IDENTITY}, {"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.35, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
        answer = data["choices"][0]["message"]["content"].strip()
        if not answer: raise RuntimeError("brain returned an empty response")
        return answer
