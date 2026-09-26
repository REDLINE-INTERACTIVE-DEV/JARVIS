import asyncio

from backend.app.missions import MissionSupervisor
from backend.app.robots import RobotFleetCoordinator, RobotJob


def test_mission_supervisor_verifies_completed_fleet():
    async def worker(job):
        await asyncio.sleep(0.001)
        return f"ack:{job.robot_id}:{job.command}"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        supervisor = MissionSupervisor(worker, fleet=fleet)
        report = await supervisor.run(
            "coordinate a five-unit inspection",
            [RobotJob(f"r{i}", "hold position") for i in range(1, 6)],
        )
        assert report.verified is True
        assert report.failed_robots == []
        assert len(report.results) == 5
        assert len(supervisor.states()) == 5
        assert {state.status for state in fleet.states()} == {"completed"}

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
