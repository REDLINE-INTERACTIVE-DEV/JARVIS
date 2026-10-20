import json

from desktop.main import (CONFIG_PATH, EXPECTED_BRAIN, JarvisClient, is_public_https_endpoint, load_saved_token, save_endpoint_config, save_token_secure)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


def test_endpoint_requires_public_https_base_url():
    assert is_public_https_endpoint("https://example.trycloudflare.com")
    assert is_public_https_endpoint("https://example.trycloudflare.com/")
    assert not is_public_https_endpoint("http://example.trycloudflare.com")
    assert not is_public_https_endpoint("https://localhost:8000")
    assert not is_public_https_endpoint("https://127.0.0.1:8000")
    assert not is_public_https_endpoint("https://192.168.1.20")
    assert not is_public_https_endpoint("https://example.trycloudflare.com/chat")
    assert not is_public_https_endpoint("https://user:pass@example.com")
    assert not is_public_https_endpoint("https://example.com?token=secret")


def test_health_uses_protected_auth_check_and_expected_brain(monkeypatch):
    token = "t" * 43
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse({"authenticated": True, "brain": EXPECTED_BRAIN})

    monkeypatch.setattr("desktop.main.urlopen", fake_urlopen)
    client = JarvisClient("https://example.trycloudflare.com", token)

    assert client.health() is True
    request, timeout = calls[0]
    assert request.full_url.endswith("/auth/check")
    assert request.get_header("X-jarvis-token") == token
    assert timeout == 5


def test_health_rejects_wrong_brain_identity(monkeypatch):
    monkeypatch.setattr(
        "desktop.main.urlopen",
        lambda request, timeout: FakeResponse({"authenticated": True, "brain": "wrong-brain"}),
    )
    client = JarvisClient("https://example.trycloudflare.com", "t" * 43)
    assert client.health() is False


def test_chat_sends_token_and_parses_response(monkeypatch):
    token = "t" * 43
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse({"response": "Hello from JARVIS."})

    monkeypatch.setattr("desktop.main.urlopen", fake_urlopen)
    client = JarvisClient("https://example.trycloudflare.com", token)

    assert client.chat("hello") == "Hello from JARVIS."
    request, timeout = calls[0]
    assert request.full_url.endswith("/chat")
    assert request.get_header("X-jarvis-token") == token
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {"message": "hello"}
    assert timeout == 60


def test_chat_refuses_to_send_without_token():
    client = JarvisClient("https://example.trycloudflare.com", "")
    try:
        client.chat("hello")
    except Exception as exc:
        assert "token" in str(exc).lower()
    else:
        raise AssertionError("chat should reject a missing token")



def test_token_uses_keyring_and_is_not_written_to_endpoint_config(tmp_path, monkeypatch):
    token = "k" * 43
    stored = {}
    fake_keyring = type(
        "FakeKeyring",
        (),
        {
            "set_password": staticmethod(lambda service, username, value: stored.update({(service, username): value})),
            "get_password": staticmethod(lambda service, username: stored.get((service, username))),
        },
    )
    monkeypatch.setitem(__import__("sys").modules, "keyring", fake_keyring)
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    monkeypatch.setattr("desktop.main.CONFIG_PATH", tmp_path / "desktop.json")

    assert save_token_secure(token) is True
    assert load_saved_token() == token
    save_endpoint_config("https://example.trycloudflare.com")
    config = json.loads((tmp_path / "desktop.json").read_text(encoding="utf-8"))
    assert config == {"endpoint": "https://example.trycloudflare.com"}
    assert token not in (tmp_path / "desktop.json").read_text(encoding="utf-8")
