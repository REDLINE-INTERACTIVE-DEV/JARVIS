"""Multi-goal orchestration primitives for the independent JARVIS brain."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class Goal:
    goal_id: str
    text: str


class MultiTaskCoordinator:
    """Run independent conversational/reasoning goals concurrently.

    Dependencies can be represented by callers by awaiting earlier goals before
    submitting a dependent goal. Independent goals never block one another.
    """

    MAX_GOALS = 8

    @classmethod
    def split_goals(cls, request: str) -> list[Goal]:
        text = request.strip()
        if not text:
            return []
        parts = [p.strip() for p in text.replace("\n", ";").split(";") if p.strip()]
        if len(parts) == 1:
            lowered = parts[0].lower()
            for marker in (" and also ", " also "):
                if marker in lowered:
                    idx = lowered.index(marker)
                    parts = [parts[0][:idx].strip(), parts[0][idx + len(marker):].strip()]
                    break
        if len(parts) > cls.MAX_GOALS:
            raise ValueError(f"at most {cls.MAX_GOALS} independent goals are supported")
        return [Goal(str(i + 1), part) for i, part in enumerate(parts)]

    async def run(self, goals: list[Goal], worker: Callable[[Goal], Awaitable[str]]) -> list[dict[str, str]]:
        async def one(goal: Goal) -> dict[str, str]:
            try:
                return {"goal_id": goal.goal_id, "goal": goal.text, "status": "completed", "result": await worker(goal)}
            except Exception as exc:
                return {"goal_id": goal.goal_id, "goal": goal.text, "status": "failed", "result": str(exc)}

        return list(await asyncio.gather(*(one(goal) for goal in goals)))


__all__ = ["Goal", "MultiTaskCoordinator"]
