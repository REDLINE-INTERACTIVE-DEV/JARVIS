from fastapi.testclient import TestClient
from backend.app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()["status"]=="ok"
def test_chat_memory():
 r=client.post("/chat",json={"message":"hello"}); assert r.status_code==200 and r.json()["response"]
 assert client.get("/memory").json()["items"]
def test_destructive_gate():
 r=client.post("/tools/call",json={"name":"computer","arguments":{"action":"delete_file"}}).json(); assert r["confirmation_required"] is True