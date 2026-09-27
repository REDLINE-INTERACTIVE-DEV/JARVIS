"""Escalating 100-message JARVIS verification matrix."""
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.memory import MemoryStore
from backend.app.research import ResearchEngine, SearchResult


def make_client(tmp_path):
    provider = Mock(spec=ResearchEngine)
    provider.search.side_effect = lambda query, limit=5: [
        SearchResult(
            title=f"Research result for {query}",
            url="https://example.com/research",
            snippet=f"Verified test result for {query}",
        )
    ]
    return TestClient(
        create_app(
            memory=MemoryStore(str(tmp_path / "jarvis-stress.db")),
            research=provider,
        )
    ), provider


def message_for(index: int) -> str:
    level = index // 10
    item = index % 10 + 1
    prompts = [
        f"Hello JARVIS, give me a concise helpful reply. Test item {item}.",
        f"Explain why the sky appears blue in simple terms. Test item {item}.",
        f"Solve this reasoning task: if A is older than B and B is older than C, who is youngest? Explain briefly. Test item {item}.",
        f"Follow these constraints: answer in two sentences, state one assumption, and do not invent facts. Explain how a battery powers a device. Test item {item}.",
        f"Compare renewable and fossil energy using exactly three dimensions and clearly separate facts from trade-offs. Test item {item}.",
        f"search for the history and major milestones of the Apollo program, then summarize the supplied research without inventing missing details. Test item {item}.",
        f"search for the history of the internet and synthesize the research into a chronological explanation, explicitly noting that the search provider is the source. Test item {item}.",
        f"search for evidence about how solar panels generate electricity, then reason through the conversion from sunlight to usable electrical power while distinguishing researched claims from reasoning. Test item {item}.",
        f"search for information about computer memory, then reason through how RAM differs from persistent storage and reconcile the two parts into one coherent answer. Test item {item}.",
        f"search for information about the scientific method, synthesize the research, identify the main steps, compare observation with hypothesis testing, and explain the result without inventing sources. Test item {item}.",
    ]
    return prompts[level]


def test_100_escalating_typed_messages(tmp_path):
    client, provider = make_client(tmp_path)
    for index in range(100):
        response = client.post("/chat", json={"message": message_for(index)})
        assert response.status_code == 200, (index + 1, response.text)
        body = response.json()
        assert body.get("response", "").strip(), f"empty response at message {index + 1}"
        if index // 10 >= 5:
            assert body["searched"] is True, f"research level failed at message {index + 1}"
    assert provider.search.call_count == 50
    memory = client.get("/memory?limit=250")
    assert memory.status_code == 200
    assert len(memory.json()["items"]) >= 200


def test_voice_transcript_3_2_matrix(tmp_path):
    client, _ = make_client(tmp_path)
    voice_cases = [
        "Hello JARVIS, can you help me?",
        "search for the latest information about how eclipses happen",
        "Reason through this: if two machines process four tasks each, how many tasks are processed?",
    ]
    for transcript in voice_cases:
        response = client.post("/chat", json={"message": transcript})
        assert response.status_code == 200
        assert response.json()["response"].strip()

    for index in range(100):
        transcript = (
            f"search for a concise explanation of item {index + 1}"
            if index % 2
            else f"Voice command {index + 1}: explain one useful fact about computers."
        )
        response = client.post("/chat", json={"message": transcript})
        assert response.status_code == 200
        body = response.json()
        assert body["response"].strip()
        if index % 2:
            assert body["searched"] is True
