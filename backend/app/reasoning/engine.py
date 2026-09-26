"""Independent deterministic planning and verification engine for JARVIS."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ReasoningStep:
    step_id: str
    objective: str
    dependencies: tuple[str, ...] = ()
    status: StepStatus = StepStatus.PENDING
    result: str = ""


@dataclass
class ReasoningPlan:
    objective: str
    steps: list[ReasoningStep] = field(default_factory=list)


class ReasoningEngine:
    """Dependency-aware concurrent reasoning/orchestration engine."""

    def __init__(self, max_concurrency: int = 16) -> None:
        self.max_concurrency = max(1, min(max_concurrency, 64))

    def plan(self, objective: str, steps: list[ReasoningStep]) -> ReasoningPlan:
        objective = objective.strip()
        if not objective:
            raise ValueError("objective is required")
        ids = {step.step_id for step in steps}
        if len(ids) != len(steps):
            raise ValueError("step ids must be unique")
        for step in steps:
            if step.step_id in step.dependencies:
                raise ValueError("a step cannot depend on itself")
            unknown = set(step.dependencies) - ids
            if unknown:
                raise ValueError(f"unknown dependencies: {sorted(unknown)}")
        self._assert_acyclic(steps)
        return ReasoningPlan(objective, list(steps))

    async def execute(self, plan: ReasoningPlan, worker: Callable[[ReasoningStep], Awaitable[str]]) -> ReasoningPlan:
        steps = {step.step_id: step for step in plan.steps}
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_step(step: ReasoningStep) -> None:
            async with semaphore:
                step.status = StepStatus.RUNNING
                try:
                    step.result = await worker(step)
                    step.status = StepStatus.COMPLETED
                except Exception as exc:
                    step.result = str(exc)
                    step.status = StepStatus.FAILED

        while True:
            pending = [step for step in steps.values() if step.status == StepStatus.PENDING]
            if not pending:
                break
            failed_ids = {step.step_id for step in steps.values() if step.status in {StepStatus.FAILED, StepStatus.BLOCKED}}
            ready = [step for step in pending if not (set(step.dependencies) & failed_ids) and all(steps[dep].status == StepStatus.COMPLETED for dep in step.dependencies)]
            for step in pending:
                if set(step.dependencies) & failed_ids:
                    step.status = StepStatus.BLOCKED
                    step.result = "blocked by a failed dependency"
            if not ready:
                remaining = [step.step_id for step in pending if step.status == StepStatus.PENDING]
                if remaining:
                    raise RuntimeError(f"reasoning plan made no progress: {remaining}")
            if ready:
                await asyncio.gather(*(run_step(step) for step in ready))
        return plan

    @staticmethod
    def _assert_acyclic(steps: list[ReasoningStep]) -> None:
        graph = {step.step_id: step.dependencies for step in steps}
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("reasoning plan contains a dependency cycle")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)
        for node in graph:
            visit(node)
