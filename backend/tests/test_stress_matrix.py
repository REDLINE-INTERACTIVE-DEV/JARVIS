from unittest.mock import Mock
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.memory import MemoryStore
from backend.app.research import ResearchEngine, SearchResult

class DeterministicBrain:
    provider="test-brain"
    def respond(self,message,memories): return f"JARVIS reply {message}"
    def answer_with_research(self,message,memories,results): return f"JARVIS researched reply {message}: {len(results)} sources"

def make_stress_client(tmp_path,research=None):
    return TestClient(create_app(memory=MemoryStore(str(tmp_path/"stress.db")),brain=DeterministicBrain(),research=research or ResearchEngine()))

def test_ten_research_messages_each_return_a_reply(tmp_path):
    provider=Mock(spec=ResearchEngine); provider.search.side_effect=lambda query,limit=5:[SearchResult(f"Result for {query}","https://example.com","test source")]
    provider.should_search.return_value=True; provider.clean_query.side_effect=lambda message:message
    client=make_stress_client(tmp_path,provider)
    for i in range(10):
        response=client.post("/chat",json={"message":f"research test {i}"})
        assert response.status_code==200 and response.json()["searched"] is True and response.json()["response"].strip()
    assert provider.search.call_count==10

def test_ten_reasoning_messages_each_return_a_reply(tmp_path):
    client=make_stress_client(tmp_path)
    for i in range(10):
        response=client.post("/chat",json={"message":f"reason through test problem {i}: compare two approaches"})
        assert response.status_code==200 and response.json()["response"].strip()

def test_one_hundred_distinct_chat_messages_each_return_a_reply(tmp_path):
    client=make_stress_client(tmp_path)
    for i in range(100):
        response=client.post("/chat",json={"message":f"general reliability test message number {i}"})
        assert response.status_code==200 and f"general reliability test message number {i}" in response.json()["response"]

def test_one_hundred_voice_commands_produce_reply_messages(tmp_path):
    client=make_stress_client(tmp_path)
    for i in range(100):
        command=f"voice wake command {i}: report status and acknowledge this test"
        response=client.post("/chat",json={"message":command})
        assert response.status_code==200 and command in response.json()["response"]
