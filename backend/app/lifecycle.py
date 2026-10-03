"""Persisted on-demand lifecycle for JARVIS."""
from __future__ import annotations
import json, os, tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

@dataclass
class RuntimeState:
    state: str = "sleeping"
    active_tasks: int = 0
    wake_count: int = 0
    sleep_count: int = 0
    last_wake_at: str | None = None
    last_sleep_at: str | None = None

class RuntimeLifecycle:
    """Restart-safe sleep/awake state with protection for active work."""
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("JARVIS_RUNTIME_STATE", "data/jarvis-runtime.json"))
        self._lock = RLock()
        self._state = self._load()
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
    def _load(self) -> RuntimeState:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            data["active_tasks"] = 0
            data["state"] = "sleeping"
            return RuntimeState(**{k: data[k] for k in RuntimeState.__dataclass_fields__ if k in data})
        except (OSError, ValueError, TypeError):
            return RuntimeState()
    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".jarvis-runtime-", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(self._state), f, indent=2, sort_keys=True)
                f.write("
")
            os.replace(tmp, self.path)
        finally:
            try: os.unlink(tmp)
            except FileNotFoundError: pass
    def wake(self, reason: str = "request") -> dict:
        with self._lock:
            if self._state.state != "awake":
                self._state.state, self._state.wake_count = "awake", self._state.wake_count + 1
                self._state.last_wake_at = self._now()
            self._save()
            return self.status(reason)
    def begin_task(self) -> dict:
        with self._lock:
            self._state.state = "awake"
            self._state.active_tasks += 1
            if self._state.active_tasks == 1:
                self._state.wake_count += 1
                self._state.last_wake_at = self._now()
            self._save()
            return self.status("task_started")
    def finish_task(self, auto_sleep: bool = True) -> dict:
        with self._lock:
            self._state.active_tasks = max(0, self._state.active_tasks - 1)
            if auto_sleep and self._state.active_tasks == 0:
                self._state.state = "sleeping"
                self._state.sleep_count += 1
                self._state.last_sleep_at = self._now()
            self._save()
            return self.status("task_finished")
    def sleep(self, force: bool = False) -> dict:
        with self._lock:
            if self._state.active_tasks and not force:
                raise RuntimeError("cannot sleep while a task is active")
            self._state.state = "sleeping"
            self._state.sleep_count += 1
            self._state.last_sleep_at = self._now()
            self._save()
            return self.status("manual_sleep")
    def status(self, reason: str | None = None) -> dict:
        data = asdict(self._state)
        data["can_sleep"] = self._state.active_tasks == 0
        if reason: data["reason"] = reason
        return data
