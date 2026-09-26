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
    """Execute the actions explicitly contained in a user's command as one scope.

    Safe prerequisite actions can be chained in the same explicit command with
    ';' or the word 'then'. JARVIS does not request a second confirmation for
    those explicitly requested safe steps. Destructive tool policy remains
    enforced by the tool registry.
    """

    MAX_EXPLICIT_STEPS = 16

    def __init__(self, tool_call: Callable[..., dict[str, Any]]) -> None:
        self._tool_call = tool_call

    @classmethod
    def _split_explicit_actions(cls, action_text: str) -> list[str]:
        normalized = action_text.replace(" THEN ", ";").replace(" then ", ";")
        actions = [item.strip() for item in normalized.split(";") if item.strip()]
        if not actions:
            raise ValueError("computer action is required")
        if len(actions) > cls.MAX_EXPLICIT_STEPS:
            raise ValueError("too many explicit computer actions")
        return actions

    def plan(self, request: str) -> list[TaskStep]:
        text = request.strip()
        if not text:
            raise ValueError("request is required")

        if text.lower().startswith("computer:"):
            action_text = text.split(":", 1)[1].strip()
            return [
                TaskStep("computer", {"action": action})
                for action in self._split_explicit_actions(action_text)
            ]

        return [TaskStep("respond", {"request": text})]

    @staticmethod
    def _result(
        status: TaskStatus,
        steps: list[TaskStep],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": status.value,
            "steps": [step.__dict__ for step in steps],
            "result": result,
        }

    def run(
        self,
        request: str,
        responder: Callable[[str], str],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        steps = self.plan(request)

        if steps[0].action == "computer":
            completed: list[TaskStep] = []
            results: list[dict[str, Any]] = []
            for step in steps:
                result = self._tool_call(step.action, step.arguments, confirmed=confirmed)
                if result.get("confirmation_required"):
                    return self._result(
                        TaskStatus.AWAITING_CONFIRMATION,
                        completed + [step],
                        {"results": results, "pending": result},
                    )
                if not result.get("ok"):
                    return self._result(
                        TaskStatus.FAILED,
                        completed + [step],
                        {"results": results, "failed": result},
                    )
                completed.append(step)
                results.append(result)
            return self._result(
                TaskStatus.COMPLETED,
                completed,
                {"results": results},
            )

        step = steps[0]
        try:
            answer = responder(step.arguments["request"])
        except Exception as exc:
            return self._result(
                TaskStatus.FAILED,
                [step],
                {"ok": False, "output": str(exc)},
            )

        return self._result(
            TaskStatus.COMPLETED,
            [step],
            {"ok": True, "output": answer},
        )

    async def run_async(
        self,
        request: str,
        responder: Callable[[str], Any],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Execute the task pipeline with an awaitable brain responder."""
        steps = self.plan(request)

        if steps[0].action == "computer":
            completed: list[TaskStep] = []
            results: list[dict[str, Any]] = []
            for step in steps:
                result = self._tool_call(step.action, step.arguments, confirmed=confirmed)
                if result.get("confirmation_required"):
                    return self._result(
                        TaskStatus.AWAITING_CONFIRMATION,
                        completed + [step],
                        {"results": results, "pending": result},
                    )
                if not result.get("ok"):
                    return self._result(
                        TaskStatus.FAILED,
                        completed + [step],
                        {"results": results, "failed": result},
                    )
                completed.append(step)
                results.append(result)
            return self._result(
                TaskStatus.COMPLETED,
                completed,
                {"results": results},
            )

        step = steps[0]
        try:
            answer = await responder(step.arguments["request"])
        except Exception as exc:
            return self._result(
                TaskStatus.FAILED,
                [step],
                {"ok": False, "output": str(exc)},
            )

        return self._result(
            TaskStatus.COMPLETED,
            [step],
            {"ok": True, "output": answer},
        )
