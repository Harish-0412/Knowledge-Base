"""Central LlamaIndex service backed by the local Ollama model."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from llama_index.llms.ollama import Ollama

from ..connectors.ollama_connector import OllamaConnector


CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "llm_config.json"


class LLMService:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.connector = OllamaConnector(config_path=config_path)
        self.llm: Ollama | None = None
        self.last_error: str | None = None

    def initialize_llm(self) -> Ollama:
        health = self.connector.health_check()
        if health["status"] != "PASS":
            raise RuntimeError(health["error"] or "Ollama model validation failed")
        self.llm = Ollama(
            model=os.getenv("OLLAMA_MODEL", self.config["model_name"]),
            base_url=self.connector.base_url,
            temperature=float(self.config["temperature"]),
            request_timeout=float(self.config["timeout"]),
            context_window=int(self.config["context_window"]),
        )
        return self.llm

    def generate_response(self, prompt: str) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            llm = self.llm or self.initialize_llm()
            response = llm.complete(prompt)
            self.last_error = None
            return {
                "status": "PASS",
                "response": str(response).strip(),
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": None,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "status": "FAIL",
                "response": "",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": self.last_error,
            }

    def health_check(self) -> dict[str, Any]:
        result = self.connector.health_check()
        result["llama_index_initialized"] = False
        if result["status"] == "PASS":
            try:
                self.initialize_llm()
                result["llama_index_initialized"] = True
            except Exception as exc:
                result["status"] = "FAIL"
                result["error"] = str(exc)
        return result
