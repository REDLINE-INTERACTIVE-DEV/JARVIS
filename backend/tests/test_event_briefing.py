from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.memory import MemoryStore

def make_client(tmp_path):
    return TestClient(create_app(memory=MemoryStore(str(tmp_path / "events.db"))))

def test_event_is_idempotent_and_briefed_once(tmp_path):
    client=make_client(tmp_path)
    payload={"source_device":"phone","event_type":"email","title":"Build update","content":"APK build completed","external_id":"gmail:abc123"}
    first=client.post("/events",json=payload).json()
    second=client.post("/events",json=payload).json()
    assert first["id"] == second["id"]
    briefing=client.post("/briefing/morning").json()
    assert briefing["event_count"] == 1
    assert "Build update" in briefing["response"]
    again=client.post("/briefing/morning").json()
    assert again["event_count"] == 0
    assert again["event_ids"] == []
def test_different_external_events_are_kept_separate(tmp_path):
    client=make_client(tmp_path)
    for i in range(100):
        r=client.post("/events",json={"source_device":"desktop","event_type":"message","title":f"Message {i}","content":"new","external_id":f"msg:{i}"})
        assert r.status_code==200
    assert len(client.get("/events/pending").json()["events"]) == 100
