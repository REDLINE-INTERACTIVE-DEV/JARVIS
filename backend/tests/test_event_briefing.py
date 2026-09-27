from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.memory import MemoryStore

def make_client(tmp_path):
    return TestClient(create_app(memory=MemoryStore(str(tmp_path / "events.db"))))

def test_event_is_idempotent_and_briefed_once(tmp_path):
    client=make_client(tmp_path)
    payload={"source_device":"phone","event_type":"email","title":"Build update","content":"APK build completed","external_id":"abc123","provider":"gmail","account_id":"account-a","version":"1"}
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


def test_same_external_id_different_accounts_is_not_merged(tmp_path):
    client=make_client(tmp_path)
    base={"source_device":"phone","event_type":"email","title":"Same","content":"mail","external_id":"same","provider":"gmail"}
    a=client.post("/events",json={**base,"account_id":"a"}).json()
    b=client.post("/events",json={**base,"account_id":"b"}).json()
    assert a["id"] != b["id"]

def test_cross_device_duplicate_is_one_event(tmp_path):
    client=make_client(tmp_path)
    base={"event_type":"message","title":"Hello","content":"same","external_id":"m1","provider":"android","account_id":"u"}
    a=client.post("/events",json={**base,"source_device":"phone"}).json()
    b=client.post("/events",json={**base,"source_device":"desktop"}).json()
    assert a["id"] == b["id"]

def test_sync_push_pull_cursor(tmp_path):
    client=make_client(tmp_path)
    payload={"device_id":"phone","events":[
        {"source_device":"phone","event_type":"message","title":"One","content":"1","external_id":"m1","provider":"android","account_id":"u"},
        {"source_device":"phone","event_type":"message","title":"Two","content":"2","external_id":"m2","provider":"android","account_id":"u"}]}
    assert client.post("/sync/push",json=payload).status_code == 200
    page=client.get("/sync/pull?cursor=0&limit=1").json()
    assert len(page["events"])==1 and page["has_more"] is True
    page2=client.get(f"/sync/pull?cursor={page['next_cursor']}&limit=10").json()
    assert len(page2["events"])==1

def test_sync_cursor_is_per_account(tmp_path):
    client=make_client(tmp_path)
    client.post("/sync/cursor",json={"provider":"gmail","account_id":"a","cursor":"100"})
    client.post("/sync/cursor",json={"provider":"gmail","account_id":"b","cursor":"200"})
    assert client.get("/sync/cursor?provider=gmail&account_id=a").json()["cursor"]=="100"
    assert client.get("/sync/cursor?provider=gmail&account_id=b").json()["cursor"]=="200"
