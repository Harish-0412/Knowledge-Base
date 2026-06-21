"""Run live infrastructure checks and generate machine-readable reports."""
from __future__ import annotations

import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .connectors.neo4j_connector import Neo4jConnector
from .connectors.ollama_connector import OllamaConnector
from .connectors.qdrant_connector import QdrantConnector


REPORTS_DIR = Path(__file__).resolve().parent / "reports"
DEPENDENCIES = ["llama-index", "llama-index-llms-ollama", "qdrant-client", "neo4j", "requests"]


def _write_json(name: str, payload: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validate_dependencies() -> dict[str, Any]:
    packages: dict[str, Any] = {}
    for package in DEPENDENCIES:
        try:
            packages[package] = {"status": "PASS", "version": importlib.metadata.version(package)}
        except importlib.metadata.PackageNotFoundError:
            packages[package] = {"status": "FAIL", "version": None}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["status"] == "PASS" for item in packages.values()) else "FAIL",
        "packages": packages,
    }


def main() -> int:
    dependencies = validate_dependencies()
    ollama_connector = OllamaConnector()
    ollama = ollama_connector.health_check()
    ollama["generation_works"] = False
    if ollama["status"] == "PASS":
        try:
            ollama["generation_works"] = bool(ollama_connector.test_generation("What is BIOS?"))
            if not ollama["generation_works"]:
                ollama["status"] = "FAIL"
                ollama["error"] = "Ollama returned an empty generation"
        except Exception as exc:
            ollama["status"] = "FAIL"
            ollama["error"] = str(exc)
    qdrant = QdrantConnector().health_check()
    neo4j_connector = Neo4jConnector()
    try:
        neo4j = neo4j_connector.health_check()
    finally:
        neo4j_connector.close()

    checks = [ollama["status"], qdrant["status"], neo4j["status"], dependencies["status"]]
    overall = "PASS" if all(status == "PASS" for status in checks) else "FAIL"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ollama_status": ollama,
        "qdrant_status": qdrant,
        "neo4j_status": neo4j,
        "dependency_status": dependencies["status"],
        "overall_status": overall,
        "final_status": "READY_FOR_RAG_IMPLEMENTATION" if overall == "PASS" else "VALIDATION_FAILED",
    }
    _write_json("dependency_validation.json", dependencies)
    _write_json("infrastructure_health_report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
