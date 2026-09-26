import asyncio, json
from backend.app.service import Watchdog

def test_watchdog_writes_heartbeat_and_stops(tmp_path):
    state_path = tmp_path / "service.json"; runs = 0
    async def service():
        nonlocal runs; runs += 1; watchdog.request_stop()
    watchdog = Watchdog(service, state_path=state_path, heartbeat_interval=0.2); asyncio.run(watchdog.run())
    state = json.loads(state_path.read_text()); assert state["status"] == "stopped"; assert state["restarts"] == 0; assert runs == 1

def test_watchdog_restarts_failed_service(tmp_path):
    state_path = tmp_path / "service.json"; runs = 0
    async def service():
        nonlocal runs; runs += 1
        if runs == 1: raise RuntimeError("test crash")
        watchdog.request_stop()
    watchdog = Watchdog(service, state_path=state_path, restart_delay=0.1); asyncio.run(watchdog.run())
    state = json.loads(state_path.read_text()); assert runs == 2; assert state["restarts"] == 1; assert state["status"] == "stopped"; assert state["last_error"] == "test crash"
