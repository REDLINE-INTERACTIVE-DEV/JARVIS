import asyncio
import threading

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from notebook_bridge.serve_jarvis import create_kaggle_app


def test_kaggle_bridge_requires_token_and_serves_existing_chat_api(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB_PATH", str(tmp_path / "jarvis.db"))
    token = "t" * 43
    app = create_kaggle_app(model=object(), processor=object(), api_token=token)
    app.state.jarvis_brain.respond = lambda message, memories: "Hello. I am JARVIS."

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["brain"] == "gemma-4-e4b-it-kaggle"

    denied = client.post("/chat", json={"message": "hello"})
    assert denied.status_code == 401
    assert client.get("/auth/check").status_code == 401
    assert client.get("/memory").status_code == 401
    assert client.post("/tasks", json={"message": "do something"}).status_code == 401

    accepted_check = client.get("/auth/check", headers={"X-JARVIS-Token": token})
    assert accepted_check.status_code == 200
    assert accepted_check.json() == {
        "authenticated": True,
        "brain": "gemma-4-e4b-it-kaggle",
    }

    accepted = client.post(
        "/chat",
        json={"message": "hello"},
        headers={"X-JARVIS-Token": token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["response"] == "Hello. I am JARVIS."



def test_slow_kaggle_inference_does_not_block_health_route(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB_PATH", str(tmp_path / "jarvis-slow.db"))
    token = "s" * 43
    app = create_kaggle_app(model=object(), processor=object(), api_token=token)
    started = threading.Event()
    release = threading.Event()

    def slow_respond(message, memories):
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test did not release the fake model")
        return "JARVIS response complete."

    app.state.jarvis_brain.respond = slow_respond

    async def exercise_concurrent_routes():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            chat_task = asyncio.create_task(
                client.post(
                    "/chat",
                    json={"message": "test slow inference"},
                    headers={"X-JARVIS-Token": token},
                )
            )
            assert await asyncio.to_thread(started.wait, 1), "chat did not enter the fake inference function"
            try:
                health = await asyncio.wait_for(client.get("/health"), timeout=1)
                assert health.status_code == 200
                assert health.json()["brain"] == "gemma-4-e4b-it-kaggle"
            finally:
                release.set()
            response = await asyncio.wait_for(chat_task, timeout=3)
            assert response.status_code == 200
            assert response.json()["response"] == "JARVIS response complete."

    asyncio.run(exercise_concurrent_routes())
