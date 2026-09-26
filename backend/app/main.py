from fastapi import FastAPI
from pydantic import BaseModel, Field

from .brain import LocalBrain
from .memory import MemoryStore
from .research import ResearchEngine
from .tasks import TaskEngine
from .tools import ToolRegistry
from .voice import VoiceState


def create_app(
    memory: MemoryStore | None = None,
    brain: LocalBrain | None = None,
    tools: ToolRegistry | None = None,
    research: ResearchEngine | None = None,
) -> FastAPI:
    app = FastAPI(title="JARVIS Local API", version="0.4.0")
    memory = memory or MemoryStore()
    brain = brain or LocalBrain()
    tools = tools or ToolRegistry()
    research = research or ResearchEngine()
    tasks = TaskEngine(tools.call)

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

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "brain": brain.provider,
            "research": "duckduckgo-html",
        }

    @app.get("/voice/states")
    def voice_states():
        return {"states": [state.value for state in VoiceState]}

    @app.post("/chat")
    def chat(req: ChatRequest):
        message = req.message.strip()
        memory.add("user", message)

        if research.should_search(message):
            query = research.clean_query(message)
            try:
                results = [item.as_dict() for item in research.search(query)]
                answer = brain.answer_with_research(message, memory.recent(20), results)
                memory.add("research", query)
                memory.add("assistant", answer)
                return {"response": answer, "searched": True, "results": results}
            except Exception as exc:
                answer = f"I couldn't complete the web search: {exc}"
                memory.add("assistant", answer)
                return {"response": answer, "searched": True, "results": []}

        answer = brain.respond(message, memory.recent(20))
        memory.add("assistant", answer)
        return {"response": answer, "searched": False, "results": []}

    @app.post("/search")
    def search(req: SearchRequest):
        results = [item.as_dict() for item in research.search(req.query, req.limit)]
        return {"query": req.query, "results": results}

    @app.get("/memory")
    def get_memory(limit: int = 20):
        return {"items": memory.recent(limit)}

    @app.post("/memory")
    def add_memory(req: MemoryRequest):
        return {"id": memory.add(req.kind, req.content)}

    @app.post("/tools/call")
    def call_tool(req: ToolRequest):
        return tools.call(req.name, req.arguments, req.confirmed)

    @app.post("/tasks")
    def run_task(req: TaskRequest):
        return tasks.run(
            req.message,
            responder=lambda m: brain.respond(m, memory.recent(20)),
            confirmed=req.confirmed,
        )

    return app


app = create_app()
