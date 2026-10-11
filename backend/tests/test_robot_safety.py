import asyncio
import pytest

from backend.app.robots import RobotFleetCoordinator, RobotJob
from backend.app.robots.safety import can_dispatch, validate_capabilities

SAFE = {"connected": True, "healthy": True, "emergency_stop": False, "status": "ok"}


def test_dispatch_requires_healthy_connection():
    assert can_dispatch(SAFE)
    assert not can_dispatch({**SAFE, "connected": False})
    assert not can_dispatch({**SAFE, "healthy": False})
    assert not can_dispatch({**SAFE, "emergency_stop": True})


def test_dispatch_fails_closed_on_missing_telemetry():
    assert not can_dispatch({})


def test_dispatch_requires_explicit_connected_true():
    assert not can_dispatch({"healthy": True, "emergency_stop": False})
    assert not can_dispatch({**SAFE, "connected": None})


def test_dispatch_requires_explicit_healthy_true():
    assert not can_dispatch({"connected": True, "emergency_stop": False})
    assert not can_dispatch({**SAFE, "healthy": None})


def test_dispatch_requires_explicit_emergency_stop_clear():
    assert not can_dispatch({"connected": True, "healthy": True})
    assert not can_dispatch({**SAFE, "emergency_stop": None})


def test_dispatch_rejects_fault_status():
    assert not can_dispatch({**SAFE, "status": "fault"})


def test_dispatch_rejects_error_status():
    assert not can_dispatch({**SAFE, "status": "error"})


def test_dispatch_rejects_offline_status():
    assert not can_dispatch({**SAFE, "status": "offline"})


def test_capability_validation_rejects_unknown():
    with pytest.raises(ValueError, match="unsupported robot capabilities"):
        validate_capabilities(["lights", "unknown"])


def test_capability_validation_normalizes_and_deduplicates():
    assert validate_capabilities([" Lights ", "lights", "camera"]) == ["camera", "lights"]


def test_coordinator_blocks_missing_telemetry_before_worker():
    calls = []

    async def worker(job):
        calls.append(job.robot_id)
        return "ack"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        results = await fleet.dispatch([RobotJob("r1", "move")])
        assert results[0]["status"] == "failed"
        assert "safety policy" in results[0]["result"]
        assert calls == []
        assert fleet.states()[0].status == "blocked"

    asyncio.run(run())


def test_coordinator_blocks_emergency_stop_before_worker():
    calls = []

    async def worker(job):
        calls.append(job.robot_id)
        return "ack"

    async def run():
        fleet = RobotFleetCoordinator(worker)
        fleet.update_telemetry("r1", {**SAFE, "emergency_stop": True})
        results = await fleet.dispatch([RobotJob("r1", "move")])
        assert results[0]["status"] == "failed"
        assert calls == []
        assert fleet.states()[0].status == "blocked"

    asyncio.run(run())
