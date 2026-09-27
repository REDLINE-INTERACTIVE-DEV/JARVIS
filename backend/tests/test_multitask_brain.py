import asyncio
import time

from backend.app.brain.core import LocalBrain
from backend.app.brain.multitask import MultiTaskCoordinator


def test_independent_goals_run_in_parallel():
    async def worker(goal):
        await asyncio.sleep(0.03)
        return goal.text.upper()

    async def run():
        return await MultiTaskCoordinator().run(
            MultiTaskCoordinator.split_goals("research this; remember that"),
            worker,
        )

    started = time.perf_counter()
    results = asyncio.run(run())
    elapsed = time.perf_counter() - started
    assert elapsed < 0.08
    assert [x["status"] for x in results] == ["completed", "completed"]


def test_failed_goal_does_not_erase_sibling_result():
    async def worker(goal):
        if goal.text == "bad":
            raise RuntimeError("boom")
        return "ok"

    results = asyncio.run(
        MultiTaskCoordinator().run(
            MultiTaskCoordinator.split_goals("bad; good"),
            worker,
        )
    )
    assert results[0]["status"] == "failed"
    assert results[1]["result"] == "ok"


def test_brain_has_independent_identity():
    brain = LocalBrain()
    prompt = brain._build_prompt("hello", [{"kind": "memory", "content": "likes robots"}])
    assert "You are JARVIS" in prompt
    assert "independent personal AI" in prompt
    assert "likes robots" in prompt
