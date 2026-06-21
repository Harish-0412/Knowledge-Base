"""HTTP connector for a local Ollama server."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "llm_config.json"


class OllamaConnector:
    def __init__(self, base_url: str | None = None, config_path: Path = CONFIG_PATH) -> None:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model_name = os.getenv("OLLAMA_MODEL", config["model_name"])
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", config["timeout"]))
        self.temperature = float(config["temperature"])
        self.max_tokens = int(config["max_tokens"])

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def list_models(self) -> list[str]:
        payload = self._request("GET", "/api/tags")
        return [model.get("name") or model.get("model") for model in payload.get("models", [])]

    def health_check(self) -> dict[str, Any]:
        try:
            models = self.list_models()
            model_reachable = self.model_name in models
            return {
                "status": "PASS" if model_reachable else "FAIL",
                "reachable": True,
                "model": self.model_name,
                "model_reachable": model_reachable,
                "available_models": models,
                "error": None if model_reachable else f"Required model {self.model_name!r} is not installed",
            }
        except Exception as exc:
            return {
                "status": "FAIL",
                "reachable": False,
                "model": self.model_name,
                "model_reachable": False,
                "available_models": [],
                "error": str(exc),
            }

    def test_generation(self, prompt: str = "What is BIOS?") -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        return str(self._request("POST", "/api/generate", json=payload).get("response", "")).strip()

    def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        result = self._request("POST", "/api/chat", json=payload)
        return str(result.get("message", {}).get("content", "")).strip()
