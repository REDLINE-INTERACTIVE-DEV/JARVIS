"""High-level mission supervision for the JARVIS robot fleet.

This layer keeps planning, execution, and verification separate. It does not
control motors or other physical actuators; a transport worker remains the
boundary for real hardware integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..reasoning import ReasoningEngine
from ..robots import RobotFleetCoordinator, RobotJob


@dataclass(frozen=True)
class FleetMissionReport:
    objective: str
    results: list[dict[str, str]]
    verified: bool
    failed_robots: list[str] = field(default_factory=list)


class MissionSupervisor:
    """Run a fleet mission and verify the coordinator's final state."""

    def __init__(
        self,
        worker: Callable[[RobotJob], Awaitable[str]],
        reasoning: ReasoningEngine | None = None,
    ) -> None:
        self._fleet = RobotFleetCoordinator(worker, reasoning=reasoning)

    @property
    def fleet(self) -> RobotFleetCoordinator:
        return self._fleet

    async def run(
        self, objective: str, jobs: list[RobotJob]
    ) -> FleetMissionReport:
        objective = objective.strip()
        if not objective:
            raise ValueError("mission objective is required")

        results = await self._fleet.dispatch(jobs)
        states = {state.robot_id: state for state in self._fleet.states()}
        failed: list[str] = []
        for job in jobs:
            state = states.get(job.robot_id)
            if state is None or state.status != "completed":
                failed.append(job.robot_id)

        return FleetMissionReport(
            objective=objective,
            results=results,
            verified=not failed and len(results) == len(jobs),
            failed_robots=failed,
        )

    def states(self):
        return self._fleet.states()

    def update_telemetry(self, robot_id: str, telemetry: dict[str, object]):
        return self._fleet.update_telemetry(robot_id, telemetry)
