"""Tool registry and safety gates for JARVIS actions."""
from dataclasses import dataclass
from typing import Any

DESTRUCTIVE=frozenset({"delete_file","shutdown","restart","kill_process","send_message","purchase"})

@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str
    confirmation_required: bool=False
    executed: bool=False
    def as_dict(self)->dict[str,Any]: return {"ok":self.ok,"output":self.output,"confirmation_required":self.confirmation_required,"executed":self.executed}

class ToolRegistry:
    def __init__(self): self.names={"computer"}
    def call(self,name:str,arguments:dict[str,Any]|None=None,confirmed:bool=False)->dict[str,Any]:
        arguments=arguments or {}
        if name not in self.names: return ToolResult(False,f"Unknown tool: {name}").as_dict()
        action=str(arguments.get("action","")).strip()
        if not action: return ToolResult(False,"A computer action is required.").as_dict()
        if action in DESTRUCTIVE and not confirmed: return ToolResult(False,f"Confirmation required for destructive action: {action}",confirmation_required=True).as_dict()
        if action in DESTRUCTIVE: return ToolResult(False,"The action is confirmed, but no OS executor is installed in the foundation build.").as_dict()
        return ToolResult(True,f"Safe computer action accepted: {action}").as_dict()
