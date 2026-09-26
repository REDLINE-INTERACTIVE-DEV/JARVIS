"""High-level mission supervision for the JARVIS robot fleet.

Planning, execution, and verification stay separate. Physical actuator control
remains behind the fleet worker boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..reasoning import ReasoningEngine
from ..robots import RobotFleetCoordinator, RobotJob, RobotState


@dataclass(frozen=True)
class FleetMissionReport:
    objective: str
    results: list[dict[str, str]]
    verified: bool
    failed_robots: list[str] = field(default_factory=list)
    telemetry_issues: list[str] = field(default_factory=list)


class MissionSupervisor:
    """Run fleet missions and verify execution plus available telemetry."""

    _BAD_STATUS = {"error", "failed", "fault", "offline", "disconnected", "unsafe"}

    def __init__(
        self,
        worker: Callable[[RobotJob], Awaitable[str]],
        reasoning: ReasoningEngine | None = None,
        fleet: RobotFleetCoordinator | None = None,
    ) -> None:
        self._fleet = fleet or RobotFleetCoordinator(worker, reasoning=reasoning)

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
        telemetry_issues: list[str] = []

        for job in jobs:
            state = states.get(job.robot_id)
            if state is None or state.status != "completed":
                failed.append(job.robot_id)
                continue
            telemetry_issues.extend(self._telemetry_issues(state))

        return FleetMissionReport(
            objective=objective,
            results=results,
            verified=not failed and not telemetry_issues and len(results) == len(jobs),
            failed_robots=failed,
            telemetry_issues=telemetry_issues,
        )

    def states(self) -> list[RobotState]:
        return self._fleet.states()

    def update_telemetry(
        self, robot_id: str, telemetry: dict[str, object]
    ) -> RobotState:
        return self._fleet.update_telemetry(robot_id, telemetry)

    @classmethod
    def _telemetry_issues(cls, state: RobotState) -> list[str]:
        telemetry = state.telemetry
        if not telemetry:
            return []

        issues: list[str] = []
        status = telemetry.get("status")
        if isinstance(status, str) and status.strip().lower() in cls._BAD_STATUS:
            issues.append(f"{state.robot_id}: telemetry status={status.strip().lower()}")

        if telemetry.get("healthy") is False:
            issues.append(f"{state.robot_id}: telemetry healthy=false")

        if telemetry.get("connected") is False:
            issues.append(f"{state.robot_id}: telemetry connected=false")

        if telemetry.get("emergency_stop") is True:
            issues.append(f"{state.robot_id}: emergency_stop=true")

        for key in ("fault", "error"):
            value = telemetry.get(key)
            if isinstance(value, str) and value.strip():
                issues.append(f"{state.robot_id}: telemetry {key}={value.strip()}")

        return issues
