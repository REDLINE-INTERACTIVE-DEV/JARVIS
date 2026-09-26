from fastapi import FastAPI
from pydantic import BaseModel,Field
from .memory import MemoryStore
from .brain import LocalBrain
from .tools import ToolRegistry
from .tasks import TaskEngine
app=FastAPI(title="JARVIS Local API",version="0.1.0")
memory=MemoryStore(); brain=LocalBrain(); tools=ToolRegistry(); tasks=TaskEngine()
class ChatRequest(BaseModel): message:str=Field(min_length=1,max_length=10000)
class ToolRequest(BaseModel): name:str; arguments:dict={}; confirmed:bool=False
class MemoryRequest(BaseModel): kind:str; content:str=Field(min_length=1,max_length=10000)
@app.get("/health")
def health(): return {"status":"ok","brain":"llama.cpp" if brain._llm else "local-foundation"}
@app.post("/chat")
def chat(req:ChatRequest):
 memory.add("user",req.message); answer=brain.respond(req.message,memory.recent(20)); memory.add("assistant",answer); return {"response":answer}
@app.get("/memory")
def get_memory(limit:int=20): return {"items":memory.recent(max(1,min(limit,100)))}
@app.post("/memory")
def add_memory(req:MemoryRequest): return {"id":memory.add(req.kind,req.content)}
@app.post("/tools/call")
def call_tool(req:ToolRequest): return tools.call(req.name,req.arguments,req.confirmed)
@app.post("/tasks")
def run_task(req:ChatRequest): return tasks.run(req.message)