from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_app_imports_successfully():
    assert app.title == "CompatIQ Document Intelligence Service"


def test_health_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_llm_health_returns_safe_config():
    response = client.get("/api/health/llm")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "ollama"
    assert body["model"] == "gemma4:31b"
    assert "api_key_present" in body
    assert "ollama_api_key" not in body
    assert "api_key" not in body


def test_llm_health_does_not_leak_api_key(monkeypatch):
    secret = "test-secret-key"
    monkeypatch.setenv("OLLAMA_API_KEY", secret)

    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        response = client.get("/api/health/llm")
        serialized = response.text

        assert response.status_code == 200
        assert response.json()["api_key_present"] is True
        assert secret not in serialized
    finally:
        get_settings.cache_clear()
