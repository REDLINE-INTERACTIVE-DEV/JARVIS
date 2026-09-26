"""Concurrent robot-job coordinator.

This subsystem is transport-neutral: it coordinates logical robot jobs and
telemetry, but does not directly drive motors or other physical hardware.
A future hardware adapter can implement the RobotAdapter protocol separately.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class RobotJob:
    robot_id: str
    command: str


class RobotFleetCoordinator:
    """Run independent, non-hardware robot jobs concurrently."""

    def __init__(
        self,
        worker: Callable[[RobotJob], Awaitable[str]],
        max_concurrency: int = 32,
    ):
        self._worker = worker
        self._limit = asyncio.Semaphore(max(1, min(max_concurrency, 128)))

    async def dispatch(self, jobs: list[RobotJob]) -> list[dict[str, str]]:
        async def run(job: RobotJob) -> dict[str, str]:
            async with self._limit:
                try:
                    result = await self._worker(job)
                    return {
                        "robot_id": job.robot_id,
                        "status": "completed",
                        "result": result,
                    }
                except Exception as exc:
                    return {
                        "robot_id": job.robot_id,
                        "status": "failed",
                        "result": str(exc),
                    }

        return await asyncio.gather(*(run(job) for job in jobs))
