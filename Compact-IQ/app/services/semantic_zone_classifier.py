from __future__ import annotations

from app.services.document_structure import DocumentSection


ZONE_TITLE_MAP = {
    "overview": ("overview",),
    "supported_components": ("supported components", "supported devices", "supported platforms", "supported models", "component list", "supported hardware"),
    "compatibility_requirements": (
        "compatibility requirements",
        "minimum requirements",
        "prerequisites",
        "required versions",
        "supported configuration",
        "firmware requirements",
        "driver requirements",
        "bios requirements",
        "dependency matrix",
        "platform requirements",
    ),
    "certified_configurations": ("certified configurations", "certified with", "compatibility matrix"),
    "unsupported_configurations": ("unsupported configurations", "known limitations", "restrictions", "not supported", "incompatible combinations", "unsupported platforms"),
    "known_issues": ("known issues", "issues", "caveats", "limitations"),
    "fixed_issues": ("fixed issues", "resolved issues", "corrected issues", "bug fixes", "fixes"),
    "upgrade_requirements": ("upgrade requirements", "upgrade path", "before upgrading", "update order", "installation sequence"),
    "remediation_guidance": ("remediation", "recommended action", "workaround", "recovery steps"),
    "security_updates": ("security updates", "security"),
}

BODY_OVERRIDE_SIGNALS = {
    "compatibility_requirements": ("requires", "required", "minimum", "or later", "back-flashing", "earlier than", "bios", "processor condition"),
    "unsupported_configurations": ("not supported", "unsupported", "incompatible"),
    "fixed_issues": ("fixed an issue", "corrected an issue", "added support", "bug fix"),
    "upgrade_requirements": ("before upgrading", "after upgrading", "upgrade path", "update order"),
    "remediation_guidance": ("workaround", "recommended action", "remediation", "recovery"),
}


class SemanticZoneClassifier:
    def classify(self, section: DocumentSection, position: int = 0) -> tuple[str, float, list[str]]:
        title = (section.section_title or "").lower()
        body = "\n".join(block.text for block in section.blocks).lower()
        signals: list[str] = []

        if position == 0 and any(label in body for label in ("document id", "release version", "release date", "applies to")):
            return "document_metadata", 0.95, ["top section contains document metadata labels"]

        for zone, phrases in BODY_OVERRIDE_SIGNALS.items():
            matched = [phrase for phrase in phrases if phrase in body]
            if len(matched) >= 2 or (zone == "unsupported_configurations" and matched):
                return zone, 0.88, [f"body contains {phrase}" for phrase in matched]

        for zone, phrases in ZONE_TITLE_MAP.items():
            matched = [phrase for phrase in phrases if phrase in title]
            if matched:
                return zone, 0.82, [f"title contains {phrase}" for phrase in matched]

        if body.strip() and position <= 1:
            return "overview", 0.55, ["early document section with general body text"]
        return "unknown", 0.25, []
