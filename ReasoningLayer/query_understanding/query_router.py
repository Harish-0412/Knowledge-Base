"""Route structured questions to knowledge and inventory layers."""

from __future__ import annotations

import json
from pathlib import Path


BASE = Path(__file__).resolve().parent


class QueryRouter:
    ORDER = ("Layer1", "Layer2", "Layer3")

    def __init__(self, rules_path: Path | None = None) -> None:
        path = rules_path or BASE / "query_router_rules.json"
        self.config = json.loads(path.read_text(encoding="utf-8"))

    def route(self, intent: str | list[str], entities: dict | None = None) -> dict:
        intents = [intent] if isinstance(intent, str) else intent
        layers: set[str] = set()
        for name in intents:
            layers.update(self.config["intent_routes"].get(name, []))
        entities = entities or {}
        if "device" in entities:
            layers.add("Layer2")
        if "ComplianceStatus" in intents and "device" not in entities and entities.get("component_types"):
            layers.discard("Layer2")
            layers.add("Layer1")
        if any(key in entities for key in ("rule", "violation", "root_cause")):
            layers.add("Layer3")
        return {"target_layers": [layer for layer in self.ORDER if layer in layers]}


def route_query(intent: str | list[str], entities: dict | None = None) -> dict:
    return QueryRouter().route(intent, entities)
