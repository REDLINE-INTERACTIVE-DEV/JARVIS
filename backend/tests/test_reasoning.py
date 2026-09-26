import asyncio

from backend.app.reasoning import ReasoningEngine, ReasoningStep, StepStatus
from backend.app.robots import RobotFleetCoordinator, RobotJob


def test_reasoning_runs_independent_steps_in_parallel():
    async def worker(step):
        await asyncio.sleep(0.01)
        return step.objective.upper()

    async def run():
        engine = ReasoningEngine(max_concurrency=3)
        plan = engine.plan("parallel", [ReasoningStep("a", "alpha"), ReasoningStep("b", "beta"), ReasoningStep("c", "gamma")])
        return await engine.execute(plan, worker)

    plan = asyncio.run(run())
    assert [step.status for step in plan.steps] == [StepStatus.COMPLETED] * 3
    assert [step.result for step in plan.steps] == ["ALPHA", "BETA", "GAMMA"]


def test_reasoning_blocks_failed_dependencies():
    async def worker(step):
        if step.step_id == "bad":
            raise RuntimeError("boom")
        return "ok"

    async def run():
        engine = ReasoningEngine()
        plan = engine.plan("dependency", [ReasoningStep("bad", "fail"), ReasoningStep("next", "wait", ("bad",))])
        return await engine.execute(plan, worker)

    plan = asyncio.run(run())
    assert plan.steps[0].status == StepStatus.FAILED
    assert plan.steps[1].status == StepStatus.BLOCKED


def test_five_robot_dispatch_is_concurrent_and_stateful():
    async def worker(job):
        await asyncio.sleep(0.01)
        return job.command.upper()

    async def run():
        fleet = RobotFleetCoordinator(worker)
        return await fleet.dispatch([RobotJob(str(i), "ping") for i in range(5)]), fleet.states()

    results, states = asyncio.run(run())
    assert len(results) == 5
    assert all(item["status"] == "completed" for item in results)
    assert len(states) == 5
    assert all(state.sequence == 1 for state in states)


def test_robot_fleet_rejects_sixth_job():
    async def worker(job):
        return "ok"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        return await fleet.dispatch([RobotJob(str(i), "ping") for i in range(6)])

    try:
        asyncio.run(run())
    except ValueError as exc:
        assert "five" in str(exc)
    else:
        raise AssertionError("six robots should be rejected")
