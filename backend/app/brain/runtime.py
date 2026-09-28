"""Local-only JARVIS brain runtime."""
from __future__ import annotations
import asyncio
import os
from dataclasses import dataclass
from typing import Any
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
    """Coordinate JARVIS reasoning without delegating inference to another AI service."""
    def __init__(self, brain: LocalBrain | None = None) -> None:
        self.brain = brain or LocalBrain()
        self.fastpath = FastPath()
        self.coordinator = MultiTaskCoordinator()
        self.max_concurrency = self._int_env("JARVIS_BRAIN_CONCURRENCY", 8, 1, 64)
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
        return self.brain.provider
    def stats(self) -> RuntimeStats:
        return RuntimeStats(self.provider, self.max_concurrency, self._requests, self._failures)
    async def respond(self, message: str, memories: list[dict[str, Any]]) -> str:
        message = message.strip()
        if not message: return "Please say something and I'll respond."
        fast = self.fastpath.try_answer(message)
        if fast is not None: return fast
        async with self._semaphore:
            self._requests += 1
            try: return await asyncio.to_thread(self.brain.respond, message, memories)
            except Exception:
                self._failures += 1
                return "I hit an internal brain error, but the JARVIS service is still running."
    async def multitask(self, request: str, memories: list[dict[str, Any]]) -> list[dict[str, str]]:
        goals = self.coordinator.split_goals(request)
        if not goals: return []
        async def worker(goal: Goal) -> str: return await self.respond(goal.text, memories)
        return await self.coordinator.run(goals, worker)
    async def answer_with_research(self, message: str, memories: list[dict[str, Any]], results: list[dict[str, str]]) -> str:
        async with self._semaphore:
            try: return await asyncio.to_thread(self.brain.answer_with_research, message, memories, results)
            except Exception:
                self._failures += 1
                return "I found the research, but the private response brain could not summarise it."
