"""Task planning and execution state machine for JARVIS."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class TaskStatus(str, Enum):
    PLANNING = "planning"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TaskStep:
    action: str
    arguments: dict[str, Any]


class TaskEngine:
    """Conservative task engine until real planners/executors are installed."""

    def __init__(self, tool_call: Callable[..., dict[str, Any]]) -> None:
        self._tool_call = tool_call

    def plan(self, request: str) -> list[TaskStep]:
        text = request.strip()
        if not text:
            raise ValueError("request is required")

        if text.lower().startswith("computer:"):
            action = text.split(":", 1)[1].strip()
            if not action:
                raise ValueError("computer action is required")
            return [TaskStep("computer", {"action": action})]

        return [TaskStep("respond", {"request": text})]

    def run(
        self,
        request: str,
        responder: Callable[[str], str],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        steps = self.plan(request)
        step = steps[0]

        if step.action == "computer":
            result = self._tool_call(step.action, step.arguments, confirmed=confirmed)
            if result.get("confirmation_required"):
                return {
                    "status": TaskStatus.AWAITING_CONFIRMATION.value,
                    "steps": [step.__dict__],
                    "result": result,
                }
            if not result.get("ok"):
                return {
                    "status": TaskStatus.FAILED.value,
                    "steps": [step.__dict__],
                    "result": result,
                }
            return {
                "status": TaskStatus.COMPLETED.value,
                "steps": [step.__dict__],
                "result": result,
            }

        try:
            answer = responder(step.arguments["request"])
        except Exception as exc:
            return {
                "status": TaskStatus.FAILED.value,
                "steps": [step.__dict__],
                "result": {"ok": False, "output": str(exc)},
            }

        return {
            "status": TaskStatus.COMPLETED.value,
            "steps": [step.__dict__],
            "result": {"ok": True, "output": answer},
        }
