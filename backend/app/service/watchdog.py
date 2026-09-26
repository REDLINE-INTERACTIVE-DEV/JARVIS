"""Restart-safe 24/7 service supervision for JARVIS."""
from __future__ import annotations
import asyncio, json, os, signal, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Awaitable, Callable

@dataclass(frozen=True)
class ServiceState:
    status: str
    started_at: float
    heartbeat_at: float
    restarts: int
    pid: int | None = None
    last_error: str | None = None

class Watchdog:
    def __init__(self, service: Callable[[], Awaitable[None]], state_path: str | Path | None = None, restart_delay: float | None = None, heartbeat_interval: float | None = None) -> None:
        self._service = service
        self.state_path = Path(state_path or os.getenv("JARVIS_STATE_PATH", "data/jarvis-service.json"))
        self.restart_delay = max(0.1, restart_delay or self._float_env("JARVIS_RESTART_DELAY", 2.0))
        self.heartbeat_interval = max(0.2, heartbeat_interval or self._float_env("JARVIS_HEARTBEAT_INTERVAL", 5.0))
        self._stop = asyncio.Event(); self._started_at = time.time(); self._restarts = 0; self._last_error: str | None = None
    @staticmethod
    def _float_env(name: str, default: float) -> float:
        try: return float(os.getenv(name, str(default)))
        except ValueError: return default
    def request_stop(self) -> None: self._stop.set()
    def state(self, status: str) -> ServiceState:
        return ServiceState(status, self._started_at, time.time(), self._restarts, os.getpid(), self._last_error)
    def write_state(self, status: str) -> ServiceState:
        state = self.state(status); self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(self.state_path.suffix + ".tmp"); temp.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8"); temp.replace(self.state_path); return state
    async def run(self) -> None:
        self.write_state("starting")
        while not self._stop.is_set():
            self.write_state("running"); heartbeat = asyncio.create_task(self._heartbeat())
            try:
                await self._service()
                if not self._stop.is_set(): self._last_error = "service exited unexpectedly"
            except asyncio.CancelledError: raise
            except Exception as exc: self._last_error = str(exc)
            finally:
                heartbeat.cancel(); await asyncio.gather(heartbeat, return_exceptions=True)
            if self._stop.is_set(): break
            self._restarts += 1; self.write_state("restarting")
            try: await asyncio.wait_for(self._stop.wait(), timeout=self.restart_delay)
            except asyncio.TimeoutError: pass
        self.write_state("stopped")
    async def _heartbeat(self) -> None:
        while True:
            self.write_state("running"); await asyncio.sleep(self.heartbeat_interval)

def install_signal_handlers(watchdog: Watchdog) -> None:
    loop = asyncio.get_running_loop()
    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is None: continue
        try: loop.add_signal_handler(sig, watchdog.request_stop)
        except (NotImplementedError, RuntimeError): pass
