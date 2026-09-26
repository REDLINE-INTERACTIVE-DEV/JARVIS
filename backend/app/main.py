from fastapi import FastAPI
from pydantic import BaseModel, Field

from .brain import BrainRuntime, LocalBrain
from .memory import MemoryStore
from .research import ResearchEngine
from .robots import RobotFleetCoordinator, RobotJob
from .tasks import TaskEngine
from .tools import ToolRegistry
from .voice import VoiceState


def create_app(
    memory: MemoryStore | None = None,
    brain: LocalBrain | BrainRuntime | None = None,
    tools: ToolRegistry | None = None,
    research: ResearchEngine | None = None,
) -> FastAPI:
    app = FastAPI(title="JARVIS Local API", version="0.5.0")
    memory = memory or MemoryStore()
    brain = brain or BrainRuntime()
    tools = tools or ToolRegistry()
    research = research or ResearchEngine()
    tasks = TaskEngine(tools.call)

    async def answer(message: str) -> str:
        if isinstance(brain, BrainRuntime):
            return await brain.respond(message, memory.recent(20))
        return brain.respond(message, memory.recent(20))

    async def research_answer(
        message: str, results: list[dict[str, str]]
    ) -> str:
        if isinstance(brain, BrainRuntime):
            return await brain.answer_with_research(
                message, memory.recent(20), results
            )
        return brain.answer_with_research(message, memory.recent(20), results)

    class ChatRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10_000)

    class SearchRequest(BaseModel):
        query: str = Field(min_length=1, max_length=500)
        limit: int = Field(default=5, ge=1, le=10)

    class ToolRequest(BaseModel):
        name: str = Field(min_length=1, max_length=100)
        arguments: dict = Field(default_factory=dict)
        confirmed: bool = False

    class MemoryRequest(BaseModel):
        kind: str = Field(min_length=1, max_length=100)
        content: str = Field(min_length=1, max_length=10_000)

    class TaskRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10_000)
        confirmed: bool = False

    class RobotJobRequest(BaseModel):
        robot_id: str = Field(min_length=1, max_length=100)
        command: str = Field(min_length=1, max_length=2_000)

    class RobotDispatchRequest(BaseModel):
        jobs: list[RobotJobRequest] = Field(min_length=1, max_length=128)

    @app.get("/health")
    async def health():
        if isinstance(brain, BrainRuntime):
            stats = brain.stats()
            return {
                "status": "ok",
                "brain": stats.provider,
                "brain_concurrency": stats.max_concurrency,
                "brain_requests": stats.requests,
                "brain_failures": stats.failures,
                "research": "duckduckgo-html",
            }
        return {
            "status": "ok",
            "brain": brain.provider,
            "brain_concurrency": 1,
            "research": "duckduckgo-html",
        }

    @app.get("/voice/states")
    async def voice_states():
        return {"states": [state.value for state in VoiceState]}

    @app.post("/chat")
    async def chat(req: ChatRequest):
        message = req.message.strip()
        memory.add("user", message)

        if research.should_search(message):
            query = research.clean_query(message)
            try:
                results = [item.as_dict() for item in research.search(query)]
                answer_text = await research_answer(message, results)
                memory.add("research", query)
                memory.add("assistant", answer_text)
                return {
                    "response": answer_text,
                    "searched": True,
                    "results": results,
                }
            except Exception as exc:
                answer_text = f"I couldn't complete the web search: {exc}"
                memory.add("assistant", answer_text)
                return {"response": answer_text, "searched": True, "results": []}

        answer_text = await answer(message)
        memory.add("assistant", answer_text)
        return {"response": answer_text, "searched": False, "results": []}

    @app.post("/search")
    async def search(req: SearchRequest):
        results = [item.as_dict() for item in research.search(req.query, req.limit)]
        return {"query": req.query, "results": results}

    @app.get("/memory")
    async def get_memory(limit: int = 20):
        return {"items": memory.recent(limit)}

    @app.post("/memory")
    async def add_memory(req: MemoryRequest):
        return {"id": memory.add(req.kind, req.content)}

    @app.post("/tools/call")
    async def call_tool(req: ToolRequest):
        return tools.call(req.name, req.arguments, req.confirmed)

    @app.post("/tasks")
    async def run_task(req: TaskRequest):
        return tasks.run(
            req.message,
            responder=lambda m: brain.brain.respond(m, memory.recent(20))
            if isinstance(brain, BrainRuntime)
            else brain.respond(m, memory.recent(20)),
            confirmed=req.confirmed,
        )

    async def robot_worker(job: RobotJob) -> str:
        # Logical coordination only. No physical actuator is invoked here.
        return await answer(f"Robot {job.robot_id} job: {job.command}")

    fleet = RobotFleetCoordinator(robot_worker, max_concurrency=32)

    @app.post("/robots/dispatch")
    async def dispatch_robots(req: RobotDispatchRequest):
        jobs = [RobotJob(item.robot_id, item.command) for item in req.jobs]
        return {"robots": await fleet.dispatch(jobs)}

    return app


app = create_app()
