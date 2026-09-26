"""Task planning and execution state machine for JARVIS."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

class TaskStatus(str, Enum):
    PLANNING="planning"; AWAITING_CONFIRMATION="awaiting_confirmation"; EXECUTING="executing"; VERIFYING="verifying"; COMPLETED="completed"; FAILED="failed"

@dataclass(frozen=True)
class TaskStep:
    action: str
    arguments: dict[str, Any]

class TaskEngine:
    def __init__(self, tool_call: Callable[..., dict[str, Any]]): self._tool_call=tool_call
    def plan(self, request: str) -> list[TaskStep]:
        text=request.strip()
        if not text: raise ValueError("request is required")
        if text.startswith("computer:"): return [TaskStep("computer", {"action": text.split(":",1)[1].strip()})]
        return [TaskStep("respond", {"request": text})]
    def run(self, request: str, responder: Callable[[str], str], confirmed: bool=False) -> dict[str, Any]:
        steps=self.plan(request); step=steps[0]
        if step.action=="computer":
            result=self._tool_call(step.action, step.arguments, confirmed=confirmed)
            status=TaskStatus.AWAITING_CONFIRMATION.value if result.get("confirmation_required") else TaskStatus.COMPLETED.value if result.get("ok") else TaskStatus.FAILED.value
            return {"status":status,"steps":[step.__dict__],"result":result}
        answer=responder(step.arguments["request"])
        return {"status":TaskStatus.COMPLETED.value,"steps":[step.__dict__],"result":{"ok":True,"output":answer}}
