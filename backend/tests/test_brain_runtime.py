from backend.app.brain import BrainRuntime, LocalBrain, MultiTaskCoordinator

def test_local_brain_is_independent_without_remote_model(monkeypatch):
    monkeypatch.delenv("JARVIS_MODEL_PATH", raising=False)
    monkeypatch.delenv("JARVIS_LLM_URL", raising=False)
    brain = LocalBrain()
    assert brain.provider == "local-foundation"
    assert "JARVIS" in brain.respond("hello", [])

def test_runtime_uses_bounded_concurrency(monkeypatch):
    monkeypatch.delenv("JARVIS_LLM_URL", raising=False)
    monkeypatch.setenv("JARVIS_BRAIN_CONCURRENCY", "16")
    runtime = BrainRuntime()
    assert runtime.max_concurrency == 16
    assert runtime.provider == runtime.brain.provider

def test_multitask_keeps_all_goals():
    import asyncio
    async def run():
        runtime = BrainRuntime()
        results = await runtime.multitask("first; second; third", [])
        return results
    results = asyncio.run(run())
    assert [x["goal"] for x in results] == ["first", "second", "third"]
    assert all(x["status"] == "completed" for x in results)
