from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.memory import MemoryStore


def make_client(tmp_path):
    return TestClient(create_app(memory=MemoryStore(str(tmp_path / "jarvis.db"))))


def test_health(tmp_path):
    response = make_client(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["brain"]


def test_voice_states(tmp_path):
    response = make_client(tmp_path).get("/voice/states")
    assert response.status_code == 200
    assert {"idle", "listening", "thinking", "speaking", "error"}.issubset(response.json()["states"])


def test_chat_and_memory(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json()["response"]
    memories = client.get("/memory").json()["items"]
    assert len(memories) >= 2
    assert memories[0]["kind"] == "assistant"


def test_memory_validation(tmp_path):
    assert make_client(tmp_path).post("/memory", json={"kind": "", "content": "x"}).status_code == 422


def test_unknown_tool(tmp_path):
    body = make_client(tmp_path).post("/tools/call", json={"name": "does_not_exist", "arguments": {}}).json()
    assert body["ok"] is False


def test_destructive_tool_is_gated(tmp_path):
    body = make_client(tmp_path).post("/tools/call", json={"name": "computer", "arguments": {"action": "delete_file"}}).json()
    assert body["confirmation_required"] is True


def test_task_confirmation_and_completion(tmp_path):
    client = make_client(tmp_path)
    pending = client.post("/tasks", json={"message": "computer:delete_file"}).json()
    assert pending["status"] == "awaiting_confirmation"
    completed = client.post("/tasks", json={"message": "computer:open_app", "confirmed": True}).json()
    assert completed["status"] == "completed"
