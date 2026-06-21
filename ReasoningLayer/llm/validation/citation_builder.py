"""Build stable, human-readable citations from evidence packages."""
from __future__ import annotations

import json
from typing import Any


class CitationBuilder:
    LABELS = {
        "Layer1": "Domain Evidence",
        "Layer2": "Inventory Evidence",
        "Layer3": "Compatibility Rule",
    }

    @classmethod
    def label_for(cls, evidence: dict[str, Any]) -> str:
        evidence_type = str(evidence.get("evidence_type", ""))
        if evidence_type == "DomainEvidence":
            return "Domain Evidence"
        if evidence_type == "InventoryEvidence":
            return "Inventory Evidence"
        if evidence_type in {"CompatibilityEvidence", "VersionEvidence", "LifecycleEvidence"}:
            return "Compatibility Rule"
        return cls.LABELS.get(str(evidence.get("source_layer", "")), "Domain Evidence")

    @classmethod
    def citation_for(cls, evidence: dict[str, Any]) -> str:
        label = cls.label_for(evidence)
        evidence_id = evidence.get("evidence_id") or evidence.get("id") or "unknown"
        return f"[{label}] {evidence_id}"

    def build(self, evidence_package: dict[str, Any]) -> list[dict[str, Any]]:
        ranked = evidence_package.get("ranked_evidence") or evidence_package.get("evidence") or []
        citations = []
        for item in ranked:
            citations.append({
                "citation": self.citation_for(item),
                "evidence_id": item.get("evidence_id") or item.get("id"),
                "type": self.label_for(item),
                "entity": item.get("entity"),
                "confidence": float(item.get("confidence", 0.0)),
                "content": item.get("content", {}),
            })
        return citations

    def format_evidence(self, evidence_package: dict[str, Any]) -> tuple[str, list[str]]:
        citations = self.build(evidence_package)
        blocks = []
        for item in citations:
            content = json.dumps(item["content"], ensure_ascii=True, sort_keys=True)
            blocks.append(
                f"{item['citation']}\nEntity: {item['entity']}\n"
                f"Confidence: {item['confidence']:.3f}\nContent: {content}"
            )
        return "\n\n".join(blocks), [item["citation"] for item in citations]
