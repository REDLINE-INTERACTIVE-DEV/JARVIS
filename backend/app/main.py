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
    app = FastAPI(title="JARVIS Local API", version="0.9.0")
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

    async def research_answer(message, results):
        if isinstance(brain, BrainRuntime):
            return await brain.answer_with_research(message, memory.recent(20), results)
        return brain.answer_with_research(message, memory.recent(20), results)

    class ChatRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10000)

    class EventRequest(BaseModel):
        source_device: str = Field(min_length=1, max_length=200)
        event_type: str = Field(min_length=1, max_length=100)
        title: str = Field(min_length=1, max_length=500)
        content: str = Field(min_length=1, max_length=20000)
        external_id: str = Field(default="", max_length=500)
        created_at: str | None = None

    class SearchRequest(BaseModel):
        query: str = Field(min_length=1, max_length=500)
        limit: int = Field(default=5, ge=1, le=100)

    class ToolRequest(BaseModel):
        name: str = Field(min_length=1, max_length=100)
        arguments: dict = Field(default_factory=dict)
        confirmed: bool = False

    class MemoryRequest(BaseModel):
        kind: str = Field(min_length=1, max_length=100)
        content: str = Field(min_length=1, max_length=10000)

    class TaskRequest(BaseModel):
        message: str = Field(min_length=1, max_length=10000)
        confirmed: bool = False

    class RobotJobRequest(BaseModel):
        robot_id: str = Field(min_length=1, max_length=100)
        command: str = Field(min_length=1, max_length=2000)

    class RobotDispatchRequest(BaseModel):
        jobs: list[RobotJobRequest] = Field(min_length=1, max_length=5)

    class RobotTelemetryRequest(BaseModel):
        robot_id: str = Field(min_length=1, max_length=100)
        telemetry: dict[str, object] = Field(default_factory=dict)

    class RobotMissionRequest(BaseModel):
        objective: str = Field(min_length=1, max_length=2000)
        jobs: list[RobotJobRequest] = Field(min_length=1, max_length=5)

    class ScreenRegisterRequest(BaseModel):
        device_id: str = Field(min_length=1, max_length=100)
        platform: str = Field(min_length=1, max_length=20)
        width: int = Field(default=0, ge=0, le=20000)
        height: int = Field(default=0, ge=0, le=20000)

    class ScreenActionRequest(BaseModel):
        action: str = Field(min_length=1, max_length=30)
        arguments: dict[str, object] = Field(default_factory=dict)

    @app.get("/health")
    async def health():
        data = {"status":"ok","brain":brain.provider,"brain_concurrency":1,"reasoning_concurrency":reasoning.max_concurrency,"robot_capacity":5,"research":"duckduckgo-html"}
        if isinstance(brain, BrainRuntime):
            s = brain.stats()
            data.update(brain=s.provider, brain_concurrency=s.max_concurrency, brain_requests=s.requests, brain_failures=s.failures)
        return data

    @app.get("/voice/states")
    async def voice_states():
        return {"states":[s.value for s in VoiceState]}

    @app.post("/chat")
    async def chat(req: ChatRequest):
        message=req.message.strip()
        memory.add("user",message)
        if research.should_search(message):
            query=research.clean_query(message)
            try:
                results=[x.as_dict() for x in research.search(query)]
                out=await research_answer(message,results)
                memory.add("research",query); memory.add("assistant",out)
                return {"response":out,"searched":True,"results":results}
            except Exception as exc:
                out=f"I couldn't complete the web search: {exc}"
                memory.add("assistant",out)
                return {"response":out,"searched":True,"results":[]}
        out=await answer(message); memory.add("assistant",out)
        return {"response":out,"searched":False,"results":[]}

    @app.post("/events")
    async def add_event(req: EventRequest):
        return memory.add_event(req.source_device, req.event_type, req.title, req.content, req.external_id, req.created_at)

    @app.get("/events/pending")
    async def pending_events(limit: int = 100):
        return {"events": memory.pending_events(limit)}

    @app.post("/briefing/morning")
    async def morning_briefing(limit: int = 100):
        events = memory.pending_events(limit)
        if not events:
            return {"response":"There is nothing new to report.", "event_count":0, "event_ids":[]}
        lines=[f"{e['event_type']}: {e['title']} — {e['content']}" for e in events]
        response="Good morning. Here is your new JARVIS briefing:\n" + "\n".join(lines)
        marked=memory.mark_events_reported([e["id"] for e in events])
        return {"response":response,"event_count":marked,"event_ids":[e["id"] for e in events]}

    @app.get("/memory")
    async def get_memory(limit:int=20):
        return {"items":memory.recent(limit)}

    @app.post("/memory")
    async def add_memory(req: MemoryRequest):
        return {"id":memory.add(req.kind,req.content)}

    @app.post("/tools/call")
    async def call_tool(req: ToolRequest):
        return tools.call(req.name,req.arguments,req.confirmed)

    @app.post("/tasks")
    async def run_task(req: TaskRequest):
        async def responder(message): return await answer(message)
        return await tasks.run_async(req.message,responder=responder,confirmed=req.confirmed)

    async def robot_worker(job): return await answer(f"Robot {job.robot_id} job: {job.command}")
    fleet=RobotFleetCoordinator(robot_worker,reasoning=reasoning); mission=MissionSupervisor(robot_worker,reasoning=reasoning,fleet=fleet)

    @app.get("/screen/devices")
    async def screen_devices(): return {"devices":[device.as_dict() for device in screen.devices()]}

    @app.post("/screen/register")
    async def register_screen(req: ScreenRegisterRequest):
        try:return screen.register(req.device_id,req.platform,req.width,req.height).as_dict()
        except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc

    @app.post("/screen/frame/{device_id}")
    async def upload_screen_frame(device_id:str,body:bytes=Body(...),content_type:str|None=Header(default=None),width:int=0,height:int=0):
        try:frame=screen.store_frame(device_id,body,content_type or "image/jpeg",width,height)
        except (KeyError,ValueError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
        return {"device_id":frame.device_id,"width":frame.width,"height":frame.height,"captured_at":frame.captured_at}

    @app.get("/screen/latest/{device_id}")
    async def latest_screen(device_id:str):
        from fastapi.responses import Response
        try:frame=screen.latest_frame(device_id)
        except KeyError as exc:raise HTTPException(status_code=404,detail="no screen frame available") from exc
        return Response(content=frame.content,media_type=frame.content_type)

    @app.post("/screen/actions/{device_id}")
    async def queue_screen_action(device_id:str,req:ScreenActionRequest):
        try:return screen.queue_action(device_id,req.action,req.arguments).as_dict()
        except (KeyError,ValueError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc

    @app.get("/screen/actions/{device_id}")
    async def get_screen_actions(device_id:str,limit:int=10):
        try:return {"actions":[item.as_dict() for item in screen.take_actions(device_id,limit)]}
        except KeyError as exc:raise HTTPException(status_code=404,detail="screen device is not registered") from exc

    @app.get("/robots/states")
    async def robot_states(): return {"capacity":5,"robots":[s.__dict__ for s in fleet.states()]}

    @app.post("/robots/telemetry")
    async def robot_telemetry(req:RobotTelemetryRequest):
        try:return fleet.update_telemetry(req.robot_id,req.telemetry).__dict__
        except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc

    @app.post("/robots/dispatch")
    async def dispatch_robots(req:RobotDispatchRequest):
        try:results=await fleet.dispatch([RobotJob(x.robot_id,x.command) for x in req.jobs])
        except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
        return {"robot_capacity":5,"robots":results}

    @app.post("/robots/mission")
    async def run_robot_mission(req:RobotMissionRequest):
        try:report=await mission.run(req.objective,[RobotJob(x.robot_id,x.command) for x in req.jobs])
        except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
        return {"objective":report.objective,"verified":report.verified,"failed_robots":report.failed_robots,"telemetry_issues":report.telemetry_issues,"robots":report.results}

    return app

app=create_app()
