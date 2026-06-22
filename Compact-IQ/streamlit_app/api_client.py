from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: float = 90.0) -> None:
        self.base_url = (base_url or os.getenv("FASTAPI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": f"Could not reach FastAPI backend: {exc}",
            }

        data: Any
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.is_success:
            return {"ok": True, "status_code": response.status_code, "data": data, "error": None}

        message = data
        if isinstance(data, dict):
            message = data.get("error", data)
        return {"ok": False, "status_code": response.status_code, "data": data, "error": message}

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/api/health")

    def db_health(self) -> dict[str, Any]:
        return self.request("GET", "/api/health/db")

    def llm_health(self) -> dict[str, Any]:
        return self.request("GET", "/api/health/llm")

    def upload_document(self, file: Any) -> dict[str, Any]:
        file_bytes = file.getvalue()
        files = {"file": (file.name, file_bytes, file.type or "application/octet-stream")}
        return self.request("POST", "/api/documents/upload", files=files)

    def list_documents(self) -> dict[str, Any]:
        return self.request("GET", "/api/documents")

    def get_document(self, document_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/documents/{document_id}")

    def run_profile(self, document_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/documents/{document_id}/profile")

    def get_profile(self, document_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/documents/{document_id}/profile")

    def run_extraction(self, document_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/documents/{document_id}/extract")

    def get_chunks(
        self,
        document_id: str,
        *,
        send_to_llm: bool | None = None,
        rule_likelihood: str | None = None,
        chunk_type: str | None = None,
        llm_usage: str | None = None,
        semantic_zone: str | None = None,
    ) -> dict[str, Any]:
        params = {}
        if send_to_llm is not None:
            params["send_to_llm"] = str(send_to_llm).lower()
        if rule_likelihood:
            params["rule_likelihood"] = rule_likelihood
        if chunk_type:
            params["chunk_type"] = chunk_type
        if llm_usage:
            params["llm_usage"] = llm_usage
        if semantic_zone:
            params["semantic_zone"] = semantic_zone
        return self.request("GET", f"/api/documents/{document_id}/chunks", params=params)

    def extract_rules(self, document_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/documents/{document_id}/extract-rules")

    def get_rule_candidates(self, document_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/documents/{document_id}/rule-candidates")

    def run_full_pipeline(self, document_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/documents/{document_id}/run-docintel-pipeline")

    def get_exports(self, document_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/documents/{document_id}/exports")

    def llm_test(self, prompt: str) -> dict[str, Any]:
        return self.request("POST", "/api/debug/llm-test", json={"prompt": prompt})


_client = ApiClient()


def configure(base_url: str) -> None:
    global _client
    _client = ApiClient(base_url)


def health() -> dict[str, Any]:
    return _client.health()


def db_health() -> dict[str, Any]:
    return _client.db_health()


def llm_health() -> dict[str, Any]:
    return _client.llm_health()


def upload_document(file: Any) -> dict[str, Any]:
    return _client.upload_document(file)


def list_documents() -> dict[str, Any]:
    return _client.list_documents()


def get_document(document_id: str) -> dict[str, Any]:
    return _client.get_document(document_id)


def run_profile(document_id: str) -> dict[str, Any]:
    return _client.run_profile(document_id)


def get_profile(document_id: str) -> dict[str, Any]:
    return _client.get_profile(document_id)


def run_extraction(document_id: str) -> dict[str, Any]:
    return _client.run_extraction(document_id)


def get_chunks(
    document_id: str,
    *,
    send_to_llm: bool | None = None,
    rule_likelihood: str | None = None,
    chunk_type: str | None = None,
    llm_usage: str | None = None,
    semantic_zone: str | None = None,
) -> dict[str, Any]:
    return _client.get_chunks(
        document_id,
        send_to_llm=send_to_llm,
        rule_likelihood=rule_likelihood,
        chunk_type=chunk_type,
        llm_usage=llm_usage,
        semantic_zone=semantic_zone,
    )


def extract_rules(document_id: str) -> dict[str, Any]:
    return _client.extract_rules(document_id)


def get_rule_candidates(document_id: str) -> dict[str, Any]:
    return _client.get_rule_candidates(document_id)


def run_full_pipeline(document_id: str) -> dict[str, Any]:
    return _client.run_full_pipeline(document_id)


def get_exports(document_id: str) -> dict[str, Any]:
    return _client.get_exports(document_id)


def llm_test(prompt: str) -> dict[str, Any]:
    return _client.llm_test(prompt)
