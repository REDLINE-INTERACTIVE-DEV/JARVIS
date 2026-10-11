import asyncio

from backend.app.missions import MissionSupervisor
from backend.app.robots import RobotFleetCoordinator, RobotJob

SAFE_TELEMETRY = {"connected": True, "healthy": True, "emergency_stop": False, "status": "ok"}


def test_mission_supervisor_verifies_completed_fleet():
    async def worker(job):
        await asyncio.sleep(0.001)
        return f"ack:{job.robot_id}:{job.command}"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        supervisor = MissionSupervisor(worker, fleet=fleet)
        jobs = [RobotJob(f"r{i}", "hold position") for i in range(1, 6)]
        for job in jobs:
            supervisor.update_telemetry(job.robot_id, SAFE_TELEMETRY)
        report = await supervisor.run("coordinate a five-unit inspection", jobs)
        assert report.verified is True
        assert report.failed_robots == []
        assert report.telemetry_issues == []
        assert len(report.results) == 5
        assert len(supervisor.states()) == 5
        assert {state.status for state in fleet.states()} == {"completed"}

    asyncio.run(run())


def test_mission_supervisor_blocks_missing_telemetry():
    calls = []

    async def worker(job):
        calls.append(job.robot_id)
        return f"ack:{job.robot_id}"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        supervisor = MissionSupervisor(worker, fleet=fleet)
        report = await supervisor.run("inspect fleet", [RobotJob("r1", "hold position")])
        assert report.verified is False
        assert report.failed_robots == ["r1"]
        assert any("telemetry unavailable" in issue for issue in report.telemetry_issues)
        assert calls == []

    asyncio.run(run())


def test_mission_supervisor_marks_unsafe_telemetry_unverified():
    calls = []

    async def worker(job):
        calls.append(job.robot_id)
        return f"ack:{job.robot_id}"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        supervisor = MissionSupervisor(worker, fleet=fleet)
        supervisor.update_telemetry("r1", SAFE_TELEMETRY)
        first = await supervisor.run("inspect fleet", [RobotJob("r1", "hold position")])
        assert first.verified is True
        supervisor.update_telemetry("r1", {
            "connected": True,
            "healthy": False,
            "emergency_stop": False,
            "status": "fault",
            "error": "motor sensor",
        })
        second = await supervisor.run("inspect fleet again", [RobotJob("r1", "hold position")])
        assert second.verified is False
        assert second.failed_robots == ["r1"]
        assert len(second.telemetry_issues) == 3
        assert any("healthy is not confirmed true" in issue for issue in second.telemetry_issues)
        assert calls == ["r1"]

    asyncio.run(run())


def test_mission_supervisor_requires_objective():
    async def worker(job):
        return "ok"

    async def run():
        supervisor = MissionSupervisor(worker)
        try:
            await supervisor.run("   ", [RobotJob("r1", "idle")])
        except ValueError as exc:
            assert "objective" in str(exc)
        else:
            raise AssertionError("empty objective should fail")

    asyncio.run(run())
