import json

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.services.llm_service import LLMServiceFactory, MockLLMService, OllamaCloudLLMService


def test_mock_llm_returns_json():
    service = MockLLMService(model="gemma4")

    result = service.generate_json(
        "Extract one compatibility rule from: Windows Server 2012 requires BIOS 1.3.5 or later."
    )

    assert "rule_candidates" in result
    candidate = result["rule_candidates"][0]
    assert "review_status" not in candidate
    assert candidate["requirements"][0]["version_raw"] == "1.3.5"


def test_factory_returns_mock_when_use_mock_llm_true():
    settings = Settings(use_mock_llm=True, ollama_model="gemma4")

    service = LLMServiceFactory.create(settings)

    assert isinstance(service, MockLLMService)
    assert service.provider == "mock"


def test_real_adapter_does_not_expose_api_key_in_errors():
    secret = "super-secret-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    settings = Settings(
        use_mock_llm=False,
        ollama_base_url="https://example.invalid",
        ollama_generate_path="/api/generate",
        ollama_api_key=secret,
        ollama_model="gemma4",
    )
    service = OllamaCloudLLMService(settings=settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AppError) as exc_info:
        service.generate_json("Return JSON")

    serialized = str(exc_info.value.details) + exc_info.value.message
    assert exc_info.value.code == "llm_auth_failed"
    assert secret not in serialized
    assert "api_key" not in serialized.lower()


def test_real_adapter_handles_non_json_response_without_secret_leak():
    secret = "another-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    settings = Settings(
        use_mock_llm=False,
        ollama_base_url="https://example.invalid",
        ollama_generate_path="/api/generate",
        ollama_api_key=secret,
        ollama_model="gemma4",
    )
    service = OllamaCloudLLMService(settings=settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(AppError) as exc_info:
        service.generate_json("Return JSON")

    serialized = str(exc_info.value.details) + exc_info.value.message
    assert exc_info.value.code == "llm_invalid_json"
    assert secret not in serialized


def test_real_adapter_sends_schema_format_and_temperature_zero():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"response": "{\"rule_candidates\": []}"})

    settings = Settings(
        use_mock_llm=False,
        ollama_base_url="https://example.invalid",
        ollama_generate_path="/api/generate",
        ollama_api_key="test-key",
        ollama_model="gemma4:31b",
    )
    service = OllamaCloudLLMService(settings=settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    result = service.generate_json(
        "Return JSON",
        format_schema={"type": "object", "properties": {"rule_candidates": {"type": "array"}}},
        options={"temperature": 0},
    )

    assert result == {"rule_candidates": []}
    assert captured["format"]["type"] == "object"
    assert captured["options"] == {"temperature": 0}
