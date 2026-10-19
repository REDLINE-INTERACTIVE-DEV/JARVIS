from fastapi.testclient import TestClient

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

    # Every API route except the deliberately public health probe is protected.
    for path in ("/memory", "/voice/states", "/devices", "/screen/devices", "/robots/states"):
        assert client.get(path).status_code == 401, path
    assert client.post("/runtime/wake", json={"reason": "test"}).status_code == 401
    assert client.post("/memory", json={"kind": "test", "content": "secret"}).status_code == 401

    wrong_token = client.post(
        "/chat", json={"message": "hello"}, headers={"X-JARVIS-Token": "wrong-token"}
    )
    assert wrong_token.status_code == 401

    accepted = client.post(
        "/chat",
        json={"message": "hello"},
        headers={"X-JARVIS-Token": token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["response"] == "Hello. I am JARVIS."
