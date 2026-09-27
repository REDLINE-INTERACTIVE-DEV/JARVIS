"""Safety boundary for JARVIS physical-device control."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

SAFE_CAPABILITIES=frozenset({"telemetry","camera","navigation","gripper","lights","audio","charging"})

@dataclass(frozen=True)
class RobotSafetyPolicy:
    require_connected: bool=True
    require_healthy: bool=True
    require_emergency_stop_clear: bool=True

def validate_capabilities(capabilities:list[str])->list[str]:
    normalized=[str(x).strip().lower() for x in capabilities if str(x).strip()]
    unknown=sorted(set(normalized)-SAFE_CAPABILITIES)
    if unknown:
        raise ValueError("unsupported robot capabilities: "+", ".join(unknown))
    return sorted(set(normalized))

def can_dispatch(telemetry:Mapping[str,object],policy:RobotSafetyPolicy|None=None)->bool:
    policy=policy or RobotSafetyPolicy()
    if policy.require_connected and telemetry.get("connected") is False:return False
    if policy.require_healthy and telemetry.get("healthy") is False:return False
    if policy.require_emergency_stop_clear and telemetry.get("emergency_stop") is True:return False
    status=telemetry.get("status")
    if isinstance(status,str) and status.strip().lower() in {"error","failed","fault","offline","disconnected","unsafe"}:return False
    return True
