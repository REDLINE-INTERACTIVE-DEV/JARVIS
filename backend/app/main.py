"""FastAPI entrypoint for the independent JARVIS ecosystem."""
from __future__ import annotations

import asyncio
from fastapi import Body, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .brain import BrainRuntime, LocalBrain
from .memory import MemoryStore
from .research import ResearchEngine
from .reasoning import ReasoningEngine
from .robots import RobotFleetCoordinator, RobotJob
from .missions import MissionSupervisor
from .tasks import TaskEngine
from .tools import ToolRegistry
from .voice import VoiceState
from .screen import ScreenBridge

def create_app(memory=None, brain=None, tools=None, research=None):
    app = FastAPI(title="JARVIS Local API", version="0.11.0")
    memory = memory or MemoryStore()
    brain = brain or BrainRuntime()
    tools = tools or ToolRegistry()
    research = research or ResearchEngine()
    reasoning = ReasoningEngine(16)
    tasks = TaskEngine(tools.call)
    screen = ScreenBridge()

    async def answer(message):
        if isinstance(brain, BrainRuntime):
            return await brain.respond(message, memory.recent(20))
        return brain.respond(message, memory.recent(20))

    class ChatRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10000)

    class MultiTaskRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10000)

    # Existing request models and routes remain below this point in the repository.
    # The multi-task endpoint is intentionally independent from /chat so normal
    # conversation never gets split accidentally.
    @app.post("/chat/multitask")
    async def chat_multitask(req: MultiTaskRequest):
        if not isinstance(brain, BrainRuntime):
            return {"results": [{"goal_id": "1", "goal": req.message, "status": "completed", "result": brain.respond(req.message, memory.recent(20))}]}
        return {"results": await brain.multitask(req.message, memory.recent(20))}

    # PLACEHOLDER: preserve the existing application routes in the next merge.
    return app

app=create_app()
