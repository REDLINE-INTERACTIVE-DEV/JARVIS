from backend.app.brain import BrainRuntime, LocalBrain

def test_local_brain_ignores_remote_model_settings(monkeypatch):
    monkeypatch.delenv("JARVIS_MODEL_PATH", raising=False)
    monkeypatch.setenv("JARVIS_LLM_URL", "https://example.invalid/v1")
    monkeypatch.setenv("JARVIS_LLM_MODEL", "third-party-model")
    brain = LocalBrain()
    assert brain.provider == "local-foundation"
    assert "private language model is not loaded" in brain.respond("hello", [])

def test_runtime_has_no_remote_llm_path(monkeypatch):
    monkeypatch.setenv("JARVIS_LLM_URL", "https://example.invalid/v1")
    monkeypatch.delenv("JARVIS_MODEL_PATH", raising=False)
    runtime = BrainRuntime()
    assert runtime.provider == "local-foundation"
    assert not hasattr(runtime, "url")
    assert not hasattr(runtime, "model")

def test_runtime_uses_bounded_concurrency(monkeypatch):
    monkeypatch.setenv("JARVIS_BRAIN_CONCURRENCY", "16")
    runtime = BrainRuntime()
    assert runtime.max_concurrency == 16
    assert runtime.provider == runtime.brain.provider

def test_multitask_keeps_all_goals():
    import asyncio
    async def run():
        runtime = BrainRuntime()
        return await runtime.multitask("first; second; third", [])
    results = asyncio.run(run())
    assert [x["goal"] for x in results] == ["first", "second", "third"]
    assert all(x["status"] == "completed" for x in results)
