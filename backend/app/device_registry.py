"""Cross-device registry for the current JARVIS process."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from threading import Lock

@dataclass
class Device:
    device_id:str
    name:str
    kind:str
    capabilities:list[str]
    last_seen:str
    metadata:dict

class DeviceRegistry:
    def __init__(self): self._devices={}; self._lock=Lock()
    def register(self,device_id,name,kind,capabilities=None,metadata=None):
        device_id=device_id.strip()
        if not device_id: raise ValueError("device_id is required")
        now=datetime.now(timezone.utc).isoformat()
        with self._lock:
            old=self._devices.get(device_id)
            item=Device(device_id,name.strip() or device_id,kind.strip() or "unknown",list(capabilities or (old.capabilities if old else [])),now,dict(metadata or (old.metadata if old else {})))
            self._devices[device_id]=item
            return asdict(item)
    def heartbeat(self,device_id):
        with self._lock:
            if device_id not in self._devices: raise KeyError(device_id)
            self._devices[device_id].last_seen=datetime.now(timezone.utc).isoformat()
            return asdict(self._devices[device_id])
    def list(self):
        with self._lock:return [asdict(x) for x in self._devices.values()]
