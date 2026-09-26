"""Cross-device screen bridge for user-authorized JARVIS control."""
from __future__ import annotations
from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Any
@dataclass
class ScreenDevice:
    device_id: str
    platform: str
    width: int = 0
    height: int = 0
    connected_at: float = field(default_factory=time)
    last_seen: float = field(default_factory=time)
    def as_dict(self) -> dict[str, Any]:
        return {"device_id": self.device_id, "platform": self.platform, "width": self.width, "height": self.height, "connected_at": self.connected_at, "last_seen": self.last_seen}
@dataclass
class ScreenFrame:
    device_id: str
    content: bytes
    content_type: str
    width: int
    height: int
    captured_at: float = field(default_factory=time)
@dataclass
class ScreenAction:
    action_id: int
    action: str
    arguments: dict[str, Any]
    created_at: float = field(default_factory=time)
    def as_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "action": self.action, "arguments": self.arguments, "created_at": self.created_at}
class ScreenBridge:
    MAX_FRAME_BYTES = 4 * 1024 * 1024
    MAX_QUEUED_ACTIONS = 64
    ALLOWED_ACTIONS = frozenset({"tap", "swipe", "type", "back", "home", "recents", "click", "hotkey"})
    def __init__(self) -> None:
        self._lock = Lock()
        self._devices: dict[str, ScreenDevice] = {}
        self._frames: dict[str, ScreenFrame] = {}
        self._queues: dict[str, list[ScreenAction]] = {}
        self._next_action_id = 1
    def register(self, device_id: str, platform: str, width: int, height: int) -> ScreenDevice:
        if not device_id.strip():
            raise ValueError("device_id is required")
        if platform not in {"android", "desktop"}:
            raise ValueError("platform must be android or desktop")
        if width < 0 or height < 0:
            raise ValueError("screen dimensions cannot be negative")
        now = time()
        with self._lock:
            current = self._devices.get(device_id)
            if current is None:
                current = ScreenDevice(device_id, platform, width, height, now, now)
                self._devices[device_id] = current
                self._queues.setdefault(device_id, [])
            else:
                current.platform, current.width, current.height, current.last_seen = platform, width, height, now
            return current
    def touch(self, device_id: str, width: int = 0, height: int = 0) -> None:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise KeyError(device_id)
            device.last_seen = time()
            if width: device.width = width
            if height: device.height = height
    def store_frame(self, device_id: str, content: bytes, content_type: str, width: int, height: int) -> ScreenFrame:
        if len(content) > self.MAX_FRAME_BYTES: raise ValueError("screen frame is too large")
        if not content: raise ValueError("screen frame is empty")
        self.touch(device_id, width, height)
        frame = ScreenFrame(device_id, bytes(content), content_type or "image/jpeg", width, height)
        with self._lock: self._frames[device_id] = frame
        return frame
    def latest_frame(self, device_id: str) -> ScreenFrame:
        with self._lock:
            frame = self._frames.get(device_id)
            if frame is None: raise KeyError(device_id)
            return frame
    def queue_action(self, device_id: str, action: str, arguments: dict[str, Any]) -> ScreenAction:
        if action not in self.ALLOWED_ACTIONS: raise ValueError(f"unsupported screen action: {action}")
        with self._lock:
            if device_id not in self._devices: raise KeyError(device_id)
            queue = self._queues.setdefault(device_id, [])
            if len(queue) >= self.MAX_QUEUED_ACTIONS: raise ValueError("screen action queue is full")
            item = ScreenAction(self._next_action_id, action, dict(arguments))
            self._next_action_id += 1
            queue.append(item)
            return item
    def take_actions(self, device_id: str, limit: int = 10) -> list[ScreenAction]:
        limit = max(1, min(limit, 20))
        with self._lock:
            if device_id not in self._devices: raise KeyError(device_id)
            queue = self._queues.setdefault(device_id, [])
            items = queue[:limit]
            del queue[:limit]
            self._devices[device_id].last_seen = time()
            return items
    def devices(self) -> list[ScreenDevice]:
        with self._lock: return list(self._devices.values())
