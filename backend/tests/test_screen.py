from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.memory import MemoryStore
def client(tmp_path): return TestClient(create_app(memory=MemoryStore(str(tmp_path/"jarvis.db"))))
def test_screen_register_queue_and_dequeue(tmp_path):
    c=client(tmp_path)
    assert c.post("/screen/register",json={"device_id":"phone","platform":"android","width":1080,"height":2400}).status_code==200
    queued=c.post("/screen/actions/phone",json={"action":"tap","arguments":{"x":100,"y":200}}).json()
    assert queued["action"]=="tap"
    assert c.get("/screen/actions/phone").json()["actions"]==[queued]
    assert c.get("/screen/actions/phone").json()["actions"]==[]
def test_screen_frame_round_trip(tmp_path):
    c=client(tmp_path)
    c.post("/screen/register",json={"device_id":"desktop","platform":"desktop","width":1920,"height":1080})
    payload=b"fake-jpeg"
    upload=c.post("/screen/frame/desktop?width=1920&height=1080",content=payload,headers={"content-type":"image/jpeg"})
    assert upload.status_code==200
    latest=c.get("/screen/latest/desktop")
    assert latest.status_code==200 and latest.content==payload
def test_screen_rejects_unknown_action(tmp_path):
    c=client(tmp_path); c.post("/screen/register",json={"device_id":"phone","platform":"android"})
    assert c.post("/screen/actions/phone",json={"action":"unsupported_action","arguments":{}}).status_code==400
