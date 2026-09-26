"""Concurrent five-robot fleet coordination backed by the reasoning engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Awaitable, Callable

from ..reasoning import ReasoningEngine, ReasoningStep, StepStatus


@dataclass(frozen=True)
class RobotJob:
    robot_id: str
    command: str


@dataclass
class RobotState:
    robot_id: str
    status: str = "idle"
    last_command: str = ""
    last_result: str = ""
    telemetry: dict[str, object] = field(default_factory=dict)
    sequence: int = 0
    updated_at: float = field(default_factory=time)


class RobotFleetCoordinator:
    """Coordinate up to five robots through dependency-aware reasoning."""
    MAX_ROBOTS = 5

    def __init__(self, worker: Callable[[RobotJob], Awaitable[str]], reasoning: ReasoningEngine | None = None):
        self._worker = worker
        self._reasoning = reasoning or ReasoningEngine(max_concurrency=self.MAX_ROBOTS)
        self._states: dict[str, RobotState] = {}

    def states(self) -> list[RobotState]:
        return [self._states[key] for key in sorted(self._states)]

    def update_telemetry(self, robot_id: str, telemetry: dict[str, object]) -> RobotState:
        state = self._state(robot_id)
        state.telemetry = dict(telemetry)
        state.updated_at = time()
        return state

    async def dispatch(self, jobs: list[RobotJob]) -> list[dict[str, str]]:
        if not 1 <= len(jobs) <= self.MAX_ROBOTS:
            raise ValueError(f"JARVIS supports 1 to {self.MAX_ROBOTS} robots per dispatch")
        ids = [job.robot_id.strip() for job in jobs]
        if any(not robot_id for robot_id in ids):
            raise ValueError("robot_id is required")
        if len(set(ids)) != len(ids):
            raise ValueError("robot_id values must be unique in a dispatch")
        plan = self._reasoning.plan("parallel robot fleet dispatch", [ReasoningStep(f"robot:{job.robot_id}", job.command) for job in jobs])

        async def run_step(step: ReasoningStep) -> str:
            robot_id = step.step_id.removeprefix("robot:")
            job = next(job for job in jobs if job.robot_id == robot_id)
            state = self._state(robot_id)
            state.status = "executing"
            state.last_command = job.command
            state.sequence += 1
            state.updated_at = time()
            try:
                result = await self._worker(job)
            except Exception as exc:
                state.status = "failed"
                state.last_result = str(exc)
                state.updated_at = time()
                raise
            state.status = "completed"
            state.last_result = result
            state.updated_at = time()
            return result

        completed = await self._reasoning.execute(plan, run_step)
        by_id = {step.step_id.removeprefix("robot:"): step for step in completed.steps}
        return [{"robot_id": job.robot_id, "status": "completed" if by_id[job.robot_id].status == StepStatus.COMPLETED else "failed", "result": by_id[job.robot_id].result} for job in jobs]

    def _state(self, robot_id: str) -> RobotState:
        robot_id = robot_id.strip()
        if not robot_id:
            raise ValueError("robot_id is required")
        if robot_id not in self._states:
            if len(self._states) >= self.MAX_ROBOTS:
                raise ValueError("robot fleet limit is five robots")
            self._states[robot_id] = RobotState(robot_id=robot_id)
        return self._states[robot_id]
