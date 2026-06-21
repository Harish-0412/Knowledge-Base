"""Entity extraction for inventory, compatibility, and reasoning questions."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent


class EntityExtractor:
    COMPONENTS = {
        "bios": ("bios", "uefi", "system bios"),
        "firmware": ("firmware", "system firmware", "device firmware"),
        "operating_system": ("operating system", "windows", "linux", "ubuntu", "os"),
        "driver": ("driver", "drivers", "driver pack"),
        "security_component": ("security agent", "antivirus", "endpoint protection", "secure boot", "tpm"),
        "management_tool": ("management agent", "management tool", "mdm", "monitoring agent"),
    }
    RISKS = ("Informational", "Low", "Medium", "High", "Critical")
    RECOMMENDATIONS = ("Upgrade", "Downgrade", "Install", "Remove", "Replace", "ConfigurationChange", "Patch", "Rollback", "PolicyUpdate", "MonitoringAction")

    def __init__(self, catalog_path: Path | None = None) -> None:
        path = catalog_path or BASE / "entity_catalog.json"
        self.catalog = json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _component_version(text: str, aliases: tuple[str, ...]) -> str | None:
        alias_pattern = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
        match = re.search(rf"\b(?:{alias_pattern})\b(?:\s+(?:version|v))?\s*([0-9]+(?:\.[0-9A-Za-z_-]+)+)", text, re.I)
        return match.group(1) if match else None

    def extract(self, question: str) -> dict:
        entities: dict[str, object] = {}
        device = re.search(r"\b(?:Laptop|Device|Endpoint|Workstation|Server)[-_]?[A-Za-z0-9]+\b", question, re.I)
        if device:
            entities["device"] = device.group(0)

        for key, aliases in self.COMPONENTS.items():
            version = self._component_version(question, aliases)
            if version:
                entities[key] = version
            elif any(re.search(rf"\b{re.escape(alias)}\b", question, re.I) for alias in aliases):
                entities.setdefault("component_types", []).append(key)

        versions = re.findall(r"(?<![A-Za-z0-9])v?([0-9]+(?:\.[0-9A-Za-z_-]+)+)", question, re.I)
        if versions:
            entities["versions"] = list(dict.fromkeys(versions))

        rule = re.search(r"\b(?:CRULE|RULE)-[A-Za-z0-9-]+\b", question, re.I)
        if rule:
            entities["rule"] = rule.group(0).upper()
        document = re.search(r"\bDOC-[A-Za-z0-9-]+\b", question, re.I)
        if document:
            entities["document"] = document.group(0).upper()
        vendor = re.search(r"\bvendor\s+([A-Z][A-Za-z0-9&.-]+)", question)
        if vendor:
            entities["vendor"] = vendor.group(1)
        risks = [risk for risk in self.RISKS if re.search(rf"\b{risk}\b", question, re.I)]
        if risks:
            entities["risk"] = risks[0]
        recs = [rec for rec in self.RECOMMENDATIONS if re.search(rf"\b{re.escape(rec)}\b", question, re.I)]
        if recs:
            entities["recommendation"] = recs[0]
        violations = re.findall(r"\b(?:VIOL-[A-Z0-9-]+|(?:compatibility|compliance|dependency|version|lifecycle|security|policy|conflict|supportability|upgrade) violation)\b", question, re.I)
        if violations:
            entities["violation"] = violations[0]
        causes = re.findall(r"\b(?:RC-[A-Z0-9-]+|version mismatch|missing dependency|unsupported configuration|configuration drift|unknown state)\b", question, re.I)
        if causes:
            entities["root_cause"] = causes[0]
        return entities


def extract_entities(question: str) -> dict:
    return EntityExtractor().extract(question)
