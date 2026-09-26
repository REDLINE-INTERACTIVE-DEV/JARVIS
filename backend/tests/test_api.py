from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.brain import LocalBrain
from backend.app.main import create_app
from backend.app.memory import MemoryStore
from backend.app.research import ResearchEngine, SearchResult
from backend.app.tasks import TaskEngine


def make_client(tmp_path, research=None):
    return TestClient(
        create_app(
            memory=MemoryStore(str(tmp_path / "jarvis.db")),
            research=research or ResearchEngine(),
        )
    )


def test_health(tmp_path):
    response = make_client(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["brain"]
    assert response.json()["brain_concurrency"] >= 1
    assert response.json()["research"] == "duckduckgo-html"


def test_voice_states(tmp_path):
    response = make_client(tmp_path).get("/voice/states")
    assert response.status_code == 200
    assert {"idle", "listening", "thinking", "speaking", "error"} <= set(response.json()["states"])


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
    body = make_client(tmp_path).post(
        "/tools/call",
        json={"name": "does_not_exist", "arguments": {}},
    ).json()
    assert body["ok"] is False


def test_destructive_tool_is_gated(tmp_path):
    body = make_client(tmp_path).post(
        "/tools/call",
        json={"name": "computer", "arguments": {"action": "delete_file"}},
    ).json()
    assert body["confirmation_required"] is True


def test_task_confirmation_and_completion(tmp_path):
    client = make_client(tmp_path)
    pending = client.post("/tasks", json={"message": "computer:delete_file"}).json()
    assert pending["status"] == "awaiting_confirmation"
    completed = client.post(
        "/tasks",
        json={"message": "computer:open_app", "confirmed": True},
    ).json()
    assert completed["status"] == "completed"


def test_task_planner_rejects_blank():
    engine = TaskEngine(lambda *args, **kwargs: {"ok": True})
    try:
        engine.plan(" ")
    except ValueError as exc:
        assert str(exc) == "request is required"
    else:
        raise AssertionError("blank task should be rejected")


def test_brain_handles_blank_message():
    assert LocalBrain().respond(" ", []) == "Please say something and I'll respond."


def test_research_detection():
    assert ResearchEngine.should_search("search for the weather")
    assert ResearchEngine.clean_query("search for the weather") == "the weather"
    assert not ResearchEngine.should_search("hello search later")


def test_search_endpoint_uses_provider(tmp_path):
    provider = Mock(spec=ResearchEngine)
    provider.search.return_value = [
        SearchResult("Example", "https://example.com", "Example snippet")
    ]
    client = make_client(tmp_path, provider)
    response = client.post("/search", json={"query": "example"})
    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Example"
    provider.search.assert_called_once_with("example", 5)


def test_fastpath_solver():
    from backend.app.brain import FastPath

    assert FastPath().try_answer("calculate 12 * (3 + 2)") == "The answer is 60."


def test_robot_dispatch_runs_jobs_concurrently(tmp_path):
    import asyncio

    from backend.app.robots import RobotFleetCoordinator, RobotJob

    async def worker(job):
        await asyncio.sleep(0.01)
        return job.command.upper()

    async def run():
        fleet = RobotFleetCoordinator(worker, max_concurrency=4)
        return await fleet.dispatch([RobotJob(str(i), "ping") for i in range(4)])

    results = asyncio.run(run())
    assert len(results) == 4
    assert all(item["status"] == "completed" for item in results)


def test_health_exposes_runtime_capacity(tmp_path):
    response = make_client(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json()["brain_concurrency"] >= 1
