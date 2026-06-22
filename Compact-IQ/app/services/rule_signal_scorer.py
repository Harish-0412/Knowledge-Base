from __future__ import annotations

import re


RULE_SIGNALS = (
    "requires",
    "required",
    "minimum",
    "at least",
    "or later",
    "must",
    "must not",
    "should not",
    "not supported",
    "unsupported",
    "incompatible",
    "only supported",
    "certified with",
    "depends on",
    "before upgrading",
    "after upgrading",
    "corrected an issue",
    "fixed an issue",
    "added support",
    "back-flashing",
    "downgrade",
    "firmware",
    "bios",
    "driver",
    "os",
    "agent",
)

COMPONENT_SIGNALS = ("bios", "firmware", "driver", "os", "cpu", "processor", "hba", "raid", "agent", "windows", "vmware", "esxi", "linux")


class RuleSignalScorer:
    def score(self, text: str, *, semantic_zone: str, chunk_type: str) -> tuple[int, list[str], str]:
        lowered = text.lower()
        score = 0
        signals: list[str] = []
        if any(word in lowered for word in ("requires", "required", "must")):
            score += 3
            signals.append("requires/required/must")
        if any(word in lowered for word in ("not supported", "unsupported", "incompatible")):
            score += 3
            signals.append("unsupported/incompatible")
        if any(word in lowered for word in ("minimum", "or later", "at least")):
            score += 2
            signals.append("minimum/or later")
        if any(word in lowered for word in ("fixed", "corrected an issue", "added support", "back-flashing")):
            score += 2
            signals.append("fix/support/back-flashing")
        component_hits = [word for word in COMPONENT_SIGNALS if word in lowered]
        if component_hits:
            score += 1
            signals.extend(component_hits)
        if re.search(r"\bv?\d+(?:\.\d+)+(?:\.x)?\b", lowered):
            score += 1
            signals.append("version_pattern")
        if semantic_zone == "document_metadata" or chunk_type == "document_metadata":
            score -= 3
            signals.append("metadata_penalty")
        if semantic_zone == "overview" or chunk_type == "overview":
            score -= 2
            signals.append("overview_penalty")

        if score >= 5:
            likelihood = "high"
        elif score >= 2:
            likelihood = "medium"
        else:
            likelihood = "low"
        return score, signals, likelihood
