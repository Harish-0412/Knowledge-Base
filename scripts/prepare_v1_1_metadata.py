#!/usr/bin/env python3
"""Add conservative v1.1 metadata defaults without changing identity data."""

import json
from pathlib import Path

VENDORS = {
    "OS-001": "Microsoft", "OS-002": "Microsoft", "OS-003": "Microsoft", "OS-005": "Canonical",
    "OS-006": "Red Hat", "OS-007": "Apple", "OS-009": "Microsoft", "OS-010": "Canonical",
    "OS-012": "Apple", "SEC-005": "Apple", "SEC-006": "Apple", "SEC-007": "Apple",
    "SEC-008": "Apple", "SEC-009": "Microsoft", "MGT-004": "Microsoft", "MGT-005": "Microsoft",
    "MGT-006": "Microsoft", "MGT-007": "Microsoft", "DRV-007": "Microsoft", "DRV-008": "Microsoft",
}
INDUSTRY_STANDARDS = {"FW-006", "FW-008", "FW-009", "DRV-006"}


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "Domain_layer" / "working" / "v1.1"
    for path in sorted(root.glob("*.json")):
        entities = json.loads(path.read_text(encoding="utf-8"))
        for entity in entities:
            entity_id = entity["entity_id"]
            entity["concept_scope"] = "VendorSpecific" if entity_id in VENDORS else ("IndustryStandard" if entity_id in INDUSTRY_STANDARDS else entity.get("concept_scope", "Generic"))
            entity["vendor"] = VENDORS.get(entity_id)
            entity.setdefault("verification_status", "review_required")
            entity.setdefault("provenance", [])
            entity.setdefault("review_notes", "")
        path.write_text(json.dumps(entities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
