"""Deterministic, explainable intent classification for endpoint queries."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent


class IntentClassifier:
    def __init__(self, rules_path: Path | None = None) -> None:
        path = rules_path or BASE / "query_router_rules.json"
        self.rules = json.loads(path.read_text(encoding="utf-8"))["intent_signals"]

    @staticmethod
    def _matches(text: str, signal: str) -> bool:
        normalized = signal.lower()
        if " " in normalized:
            return normalized in text
        return re.search(rf"\b{re.escape(normalized)}\b", text) is not None

    def classify(self, question: str) -> dict:
        text = " ".join(question.lower().strip().split())
        if not text:
            return {"intent": "ConceptExplanation", "confidence": 0.0, "intents": [], "mode": "single"}

        scored: list[tuple[str, float, list[str]]] = []
        for intent, config in self.rules.items():
            hits = [signal for signal in config["signals"] if self._matches(text, signal)]
            negative_hits = [signal for signal in config.get("negative_signals", []) if self._matches(text, signal)]
            score = sum(config.get("signal_weights", {}).get(hit, 1.0) for hit in hits)
            score -= 1.5 * len(negative_hits)
            if hits and score > 0:
                scored.append((intent, score + config.get("priority", 0) / 100, hits))

        if not scored:
            fallback = "DeviceInvestigation" if re.search(r"\b(device|laptop|server|endpoint|workstation)[-_]?\w+\b", text) else "ConceptExplanation"
            return {"intent": fallback, "confidence": 0.55, "intents": [{"intent": fallback, "confidence": 0.55}], "mode": "single"}

        scored.sort(key=lambda item: (-item[1], item[0]))
        top_score = scored[0][1]
        ranked = []
        for intent, score, hits in scored:
            confidence = min(0.99, 0.56 + 0.11 * score + 0.02 * len(hits))
            if score >= max(1.0, top_score * 0.45):
                ranked.append({"intent": intent, "confidence": round(confidence, 3)})
        ranked = ranked[:3]
        return {"intent": ranked[0]["intent"], "confidence": ranked[0]["confidence"], "intents": ranked,
                "mode": "single" if len(ranked) == 1 else "multi"}


def classify_intent(question: str) -> dict:
    return IntentClassifier().classify(question)
