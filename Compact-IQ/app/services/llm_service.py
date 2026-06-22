import json
import logging
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.services.json_repair import repair_json

logger = logging.getLogger(__name__)


class LLMService(Protocol):
    provider: str

    def generate_json(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        format_schema: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict:
        ...

    def generate_text(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        ...


class MockLLMService:
    provider = "mock"

    def __init__(self, model: str = "mock-gemma") -> None:
        self.model = model

    def generate_json(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        format_schema: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "rule_candidates": [
                {
                    "rule_type": "min_version_constraint",
                    "condition_logic": "AND",
                    "conditions": [
                        {
                            "component_type": "os",
                            "component_name": self._detect_subject(prompt),
                            "component_family": None,
                            "vendor": None,
                            "operator": "installed",
                            "value_raw": self._detect_subject(prompt),
                            "version_raw": None,
                            "version_scheme": None,
                        }
                    ],
                    "requirements": [
                        {
                            "component_type": "bios",
                            "component_name": "System BIOS",
                            "component_family": None,
                            "vendor": None,
                            "operator": ">=",
                            "value_raw": None,
                            "version_raw": self._detect_version(prompt),
                            "version_scheme": "semantic",
                            "requirement_kind": "min_version",
                        }
                    ],
                    "exceptions": [],
                    "severity": "warning",
                    "confidence_score": 0.8,
                    "confidence_reason": "Deterministic mock response for local tests and demos.",
                    "remediation_hint": "Use the required BIOS version or later.",
                }
            ]
        }

    def generate_text(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        return "The Llama assistant is running in mock mode. Configure Ollama to receive a model-generated answer."

    def _detect_subject(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "windows server 2012" in lowered:
            return "Windows Server 2012"
        if "product a" in lowered:
            return "Product A"
        return "compatibility document"

    def _detect_version(self, prompt: str) -> str:
        search_text = prompt
        lower_prompt = prompt.lower()
        if "chunk text:" in lower_prompt:
            start = lower_prompt.index("chunk text:") + len("chunk text:")
            search_text = prompt[start:]
        elif "from:" in lower_prompt:
            start = lower_prompt.index("from:") + len("from:")
            search_text = prompt[start:]

        for token in search_text.replace(",", " ").split():
            stripped = token.strip(".:;()")
            if any(char.isdigit() for char in stripped) and "." in stripped:
                return stripped
        return "1.0"

    def _excerpt(self, prompt: str) -> str:
        source_marker = "source excerpt:"
        lower_prompt = prompt.lower()
        if source_marker in lower_prompt:
            start = lower_prompt.index(source_marker) + len(source_marker)
            remainder = prompt[start:].strip()
            return remainder.split("\n\n", 1)[0].strip()[:500]
        marker = "from:"
        if marker in lower_prompt:
            start = lower_prompt.index(marker) + len(marker)
            return prompt[start:].strip()[:500]
        return prompt.strip()[:500]


class OllamaCloudLLMService:
    provider = "ollama"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client

    def generate_json(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        format_schema: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict:
        timeout = timeout_seconds or self.settings.ollama_timeout_seconds
        url = self._generate_url()
        headers = {"Content-Type": "application/json"}
        if self.settings.ollama_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ollama_api_key}"

        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": format_schema or "json",
        }
        if options:
            payload["options"] = options

        try:
            if self.client is not None:
                response = self._post_with_retry(self.client, url, payload, headers, timeout)
            else:
                with httpx.Client() as client:
                    response = self._post_with_retry(client, url, payload, headers, timeout)
        except httpx.TimeoutException as exc:
            raise self._adapter_error("llm_timeout", "Ollama request timed out.", details={"timeout_seconds": timeout}) from exc
        except httpx.HTTPError as exc:
            raise self._adapter_error("llm_connection_error", "Ollama request failed before a response was received.") from exc

        if response.status_code in {401, 403}:
            raise self._adapter_error(
                "llm_auth_failed",
                "Ollama rejected the request. Check your Ollama credentials.",
                status_code=502,
                details={"http_status": response.status_code},
            )
        if response.status_code == 404:
            raise self._adapter_error(
                "llm_endpoint_not_found",
                "Ollama endpoint was not found. Check OLLAMA_GENERATE_PATH.",
                status_code=502,
                details={"http_status": response.status_code, "generate_path": self.settings.ollama_generate_path},
            )
        if response.status_code >= 400:
            raise self._adapter_error(
                "llm_http_error",
                "Ollama returned an error response.",
                status_code=502,
                details={"http_status": response.status_code},
            )

        try:
            payload_json = response.json()
        except json.JSONDecodeError as exc:
            raise self._adapter_error("llm_invalid_json", "Ollama returned a non-JSON response.", status_code=502) from exc

        return self._extract_json_payload(payload_json)

    def generate_text(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        timeout = timeout_seconds or self.settings.ollama_timeout_seconds
        url = self._generate_url()
        headers = {"Content-Type": "application/json"}
        if self.settings.ollama_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ollama_api_key}"
        payload: dict[str, Any] = {
            "model": model or self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options

        try:
            client = self.client or httpx.Client()
            response = self._post_with_retry(client, url, payload, headers, timeout)
        except httpx.TimeoutException as exc:
            raise self._adapter_error("llm_timeout", "Ollama request timed out.", details={"timeout_seconds": timeout}) from exc
        except httpx.HTTPError as exc:
            raise self._adapter_error("llm_connection_error", "Ollama request failed before a response was received.") from exc
        finally:
            if self.client is None and "client" in locals():
                client.close()

        if response.status_code in {401, 403}:
            raise self._adapter_error("llm_auth_failed", "Ollama rejected the request. Check your Ollama credentials.", details={"http_status": response.status_code})
        if response.status_code == 404:
            raise self._adapter_error("llm_endpoint_not_found", "Ollama model or endpoint was not found.", details={"http_status": 404, "model": model or self.settings.ollama_model})
        if response.status_code >= 400:
            raise self._adapter_error("llm_http_error", "Ollama returned an error response.", details={"http_status": response.status_code})

        try:
            response_json = response.json()
        except json.JSONDecodeError as exc:
            raise self._adapter_error("llm_invalid_response", "Ollama returned an invalid response.") from exc

        text = response_json.get("response")
        if not isinstance(text, str):
            message = response_json.get("message")
            text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise self._adapter_error("llm_empty_response", "Ollama returned an empty answer.")
        return text.strip()

    def _extract_json_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise self._adapter_error("llm_invalid_json", "Ollama response JSON was not an object.", status_code=502)

        if "response" in payload:
            response_value = payload["response"]
            if isinstance(response_value, dict):
                return response_value
            if isinstance(response_value, str):
                try:
                    parsed = json.loads(response_value)
                except json.JSONDecodeError as exc:
                    repair_result = repair_json(response_value)
                    if repair_result.ok and isinstance(repair_result.data, dict):
                        return repair_result.data
                    raise self._adapter_error(
                        "llm_invalid_json",
                        "Ollama response field did not contain JSON.",
                        details={"response_preview": response_value[:300]},
                    ) from exc
                if isinstance(parsed, dict):
                    return parsed
                raise self._adapter_error("llm_invalid_json", "Ollama response field JSON was not an object.")

        message = payload.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            try:
                parsed = json.loads(message["content"])
            except json.JSONDecodeError as exc:
                raise self._adapter_error("llm_invalid_json", "Ollama message content did not contain JSON.") from exc
            if isinstance(parsed, dict):
                return parsed

        return payload

    def _generate_url(self) -> str:
        base_url = self.settings.ollama_base_url.rstrip("/")
        path = self.settings.ollama_generate_path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"

    def _post_with_retry(
        self,
        client: httpx.Client,
        url: str,
        payload: dict,
        headers: dict,
        timeout: int,
        *,
        max_retries: int = 3,
    ) -> httpx.Response:
        """POST with exponential backoff on transient connection-reset errors.

        Ollama Cloud (Google Frontend) forcibly drops TCP connections when many
        requests arrive in rapid succession (e.g., one per chunk during rule
        extraction).  Retrying with a small back-off resolves this without any
        change to the core pipeline logic.
        """
        import time

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return client.post(url, json=payload, headers=headers, timeout=timeout)
            except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError) as exc:
                last_exc = exc
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "ollama transient connection error (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1,
                    max_retries,
                    wait,
                    exc,
                )
                time.sleep(wait)
        # All retries exhausted — re-raise so the outer handler can wrap it
        raise last_exc  # type: ignore[misc]

    def _adapter_error(
        self,
        code: str,
        message: str,
        status_code: int = 502,
        details: dict | None = None,
    ) -> AppError:
        safe_details = {
            "provider": self.provider,
            "model": self.settings.ollama_model,
            **(details or {}),
        }
        return AppError(code=code, message=message, status_code=status_code, details=safe_details)


class LLMServiceFactory:
    # A single persistent client shared across all calls within a process lifetime.
    # This avoids opening a new TCP connection per LLM call (which triggers
    # rate-limiting on the Ollama Cloud / Google Frontend load balancer).
    _shared_client: httpx.Client | None = None

    @classmethod
    def _get_shared_client(cls) -> httpx.Client:
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.Client(
                # Keep-alive pool: up to 5 connections, 30-second idle timeout
                limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=30),
            )
        return cls._shared_client

    @staticmethod
    def create(settings: Settings | None = None) -> LLMService:
        resolved_settings = settings or get_settings()
        if resolved_settings.use_mock_llm:
            return MockLLMService(model=resolved_settings.ollama_model)
        return OllamaCloudLLMService(
            settings=resolved_settings,
            client=LLMServiceFactory._get_shared_client(),
        )
