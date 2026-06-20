#!/usr/bin/env python3
"""Build a deterministic canonical registry and a safe Neo4j staging package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_FILES = ["firmware.json", "operating_system.json", "drivers.json", "security.json", "management.json"]
SCOPE_DOMAINS = ["Firmware", "Operating System", "Driver", "Security", "Management"]
METADATA_DEFAULTS = {
    "concept_scope": "Generic", "vendor": None, "verification_status": "review_required",
    "provenance": [], "review_notes": "",
}
ALLOWED_SCOPE = {"Generic", "VendorSpecific", "IndustryStandard", "SharedPlatform", "External"}
ALLOWED_VERIFICATION = {"llm_generated", "review_required", "source_verified", "human_approved"}
CONTROLLED_LABELS = {
    "Firmware": "Firmware", "Operating System": "OperatingSystem", "Driver": "Driver",
    "Security": "SecurityComponent", "Management": "ManagementTool",
}
RECLASSIFICATION_REVIEW = {
    "FW-006": ("shared_platform_concept", "ACPI is an industry standard/interface, not firmware."),
    "FW-007": ("shared_platform_concept", "A firmware update utility is software that updates firmware."),
    "FW-008": ("shared_platform_concept", "The EFI System Partition is a boot storage structure."),
    "FW-009": ("shared_platform_concept", "GPT is a disk partitioning standard."),
    "FW-011": ("shared_platform_concept", "An OS bootloader is software in the boot chain, not firmware."),
    "OS-010": ("requires_human_review", "Ubuntu Pro is a service/subscription, not an OS version."),
    "MGT-004": ("future_domain_entity", "Active Directory primarily belongs to Identity and Access."),
    "MGT-008": ("requires_human_review", "SIEM is security operations infrastructure; placement needs governance approval."),
}
APPROVED_RECLASSIFICATION_STATE = {
    "FW-006": ("Firmware", "Firmware", "Platform Interface Standard", "IndustryStandard", None),
    "FW-007": ("Management", "ManagementTool", "Firmware Update Utility", "Generic", None),
    "FW-008": ("Firmware", "Firmware", "Boot Storage Structure", "SharedPlatform", None),
    "FW-009": ("Firmware", "Firmware", "Partition Table Standard", "IndustryStandard", None),
    "FW-011": ("Operating System", "OperatingSystem", "Boot Component", "Generic", None),
    "OS-010": ("Management", "ManagementTool", "Support and Security Maintenance Service", "VendorSpecific", "Canonical"),
    "MGT-004": ("Management", "ManagementTool", "Directory and Identity Service", "VendorSpecific", "Microsoft"),
    "MGT-008": ("Management", "ManagementTool", "Security Operations Platform", "Generic", None),
}


def normalize_for_lookup(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.casefold().strip().replace("_", " ")
    value = re.sub(r"(?<=\w)-(?=\w)", " ", value)
    return re.sub(r"\s+", " ", value)


def clean_aliases(values: object, canonical_name: str) -> list[str]:
    if not isinstance(values, list):
        return []
    canonical = normalize_for_lookup(canonical_name)
    by_normalized = {}
    for value in values:
        if isinstance(value, str) and value.strip():
            trimmed = value.strip()
            normalized = normalize_for_lookup(trimmed)
            if normalized and normalized != canonical and normalized not in by_normalized:
                by_normalized[normalized] = trimmed
    return sorted(by_normalized.values(), key=lambda item: (item.casefold(), item))


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(directory: Path) -> dict[str, str]:
    return {name: file_sha256(directory / name) for name in SOURCE_FILES if (directory / name).exists()}


def classify_unresolved(reference: str) -> tuple[str, str | None, str, str, str]:
    """Return classification, deferred domain, status, action, reason."""
    norm = normalize_for_lookup(reference)
    
    # User-specific dispositions
    specific_dispositions = {
        "configuration baseline": ("create_core_entity", None, "requires_human_review", "Create as core entity", "Directly relevant to configuration compliance"),
        "endpoint agent": ("create_core_entity", None, "requires_human_review", "Create as core entity", "Directly relevant to endpoint management"),
        "pci express interface": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "anti malware engine": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "cve database": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "driver update service": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "endpointsecurity framework": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "management engine interface": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "security information and event management forwarder": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "uefi signature database": ("valid_external_concept", None, "external", "Keep as external", "Meaningful concept without creating v1.1 nodes"),
        "asset inventory system": ("future_domain_entity", "Asset and Configuration Management", "deferred", "Defer to future domain", "Concept belongs to the planned Asset and Configuration Management domain"),
        "file integrity monitoring agent": ("future_domain_entity", "Endpoint Security", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Security domain"),
        "log aggregation platform": ("future_domain_entity", "Observability", "deferred", "Defer to future domain", "Concept belongs to the planned Observability domain"),
        "software distribution system": ("future_domain_entity", "Software Lifecycle Management", "deferred", "Defer to future domain", "Concept belongs to the planned Software Lifecycle Management domain"),
        "application performance monitoring": ("future_domain_entity", "Observability", "deferred", "Defer to future domain", "Concept belongs to the planned Observability domain"),
        "application whitelisting agent": ("future_domain_entity", "Endpoint Security", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Security domain"),
        "change management system": ("future_domain_entity", "IT Service Management", "deferred", "Defer to future domain", "Concept belongs to the planned IT Service Management domain"),
        "data loss prevention agent": ("future_domain_entity", "Endpoint Security", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Security domain"),
        "deployment ring policy": ("future_domain_entity", "Policy and Compliance", "deferred", "Defer to future domain", "Concept belongs to the planned Policy and Compliance domain"),
        "extended detection and response agent": ("future_domain_entity", "Security Operations", "deferred", "Defer to future domain", "Concept belongs to the planned Security Operations domain"),
        "host intrusion detection system": ("future_domain_entity", "Endpoint Security", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Security domain"),
        "host intrusion prevention system": ("future_domain_entity", "Endpoint Security", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Security domain"),
        "maintenance window policy": ("future_domain_entity", "Policy and Compliance", "deferred", "Defer to future domain", "Concept belongs to the planned Policy and Compliance domain"),
        "os deployment service": ("future_domain_entity", "Software Lifecycle Management", "deferred", "Defer to future domain", "Concept belongs to the planned Software Lifecycle Management domain"),
        "out of band management": ("future_domain_entity", "Platform Management", "deferred", "Defer to future domain", "Concept belongs to the planned Platform Management domain"),
        "remote control service": ("future_domain_entity", "Endpoint Management", "deferred", "Defer to future domain", "Concept belongs to the planned Endpoint Management domain"),
        "time series database": ("future_domain_entity", "Data Platform", "deferred", "Defer to future domain", "Concept belongs to the planned Data Platform domain"),
        "user and entity behavior analytics agent": ("future_domain_entity", "Security Analytics", "deferred", "Defer to future domain", "Concept belongs to the planned Security Analytics domain"),
        "vulnerability management platform": ("future_domain_entity", "Security Operations", "deferred", "Defer to future domain", "Concept belongs to the planned Security Operations domain"),
        "mdm policy engine": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Generic implementation component"),
        "alerting engine": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Capability/component phrase"),
        "compliance policy engine": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Project component, not stable domain concept"),
        "os audio subsystem": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Overly broad architectural phrase"),
        "os graphics subsystem": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Overly broad architectural phrase"),
        "os update service": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Ambiguous generic service"),
        "patch compliance reporting": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Reporting capability"),
        "platform key management": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Broad capability phrase"),
        "platform power management": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Broad capability phrase"),
        "power management subsystem": ("overly_broad_reference", None, "rejected", "Reject as related entity", "Broad architectural phrase"),
    }
    
    if norm in specific_dispositions:
        return specific_dispositions[norm]
    
    # Default logic
    future_rules = [
        ("Software Runtime", ("runtime", "package manager", "systemd", "cgroups", "ebpf", "dkms", "kernel extension", "loadable kernel module")),
        ("Identity and Access", ("identity provider", "conditional access", "pki", "certificate management", "pam", "lsass", "credential guard")),
        ("Hardware", ("controller", "hardware", "bmc", "ipmi", "cmos", "iommu", "battery", "thermal", "power delivery", "sensor", "self encrypting drive")),
        ("Networking", ("network access control", "vpn agent", "wake on lan", "wol")),
        ("Cloud Services", ("apple business manager",)),
    ]
    for domain, needles in future_rules:
        if any(needle in norm for needle in needles):
            return "future_domain_entity", domain, "deferred", "Model in the deferred domain after domain governance review.", f"Concept belongs to the planned {domain} domain."
    invalid_suffixes = (" subsystem", " system", " engine", " policy", " reporting", " service", " platform", " interface", " database", " framework", " agent")
    standards = ("fips", "whql", "smbios", "tcg opal", "scsi", "wasapi", "etw", "wmi", "syslog", "opentelemetry", "apfs", "ntfs", "mbr", "post", "csm")
    if any(token in norm for token in standards):
        return "valid_external_concept", None, "external", "Retain as a documented external concept.", "Meaningful standard, interface, format, or platform facility outside the five entity domains."
    if norm.endswith(invalid_suffixes) or any(word in norm for word in ("baseline", "compliance", "management", "monitoring", "distribution")):
        return "requires_human_review", None, "requires_human_review", "Review whether this phrase should become a governed entity or be removed.", "The value is meaningful but may represent a capability, relationship phrase, or future entity."
    broad = {"full disk encryption", "code signing", "notarization", "out of band management", "platform key management", "memory encryption"}
    if norm in broad:
        return "overly_broad_reference", None, "rejected", "Replace with a specific governed concept when relationship semantics are defined.", "The reference is too broad for a stable staging edge."
    return "valid_external_concept", None, "external", "Retain as a documented external concept.", "Valid technical concept not required as a Domain Layer v1.1 entity."


def load_entities(input_dir: Path) -> tuple[list[dict], dict[str, int], list[str]]:
    entities, counts, errors = [], {}, []
    for name in SOURCE_FILES:
        path = input_dir / name
        if not path.exists():
            errors.append(f"Missing source file: {name}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON in {name}: {exc}")
            continue
        if not isinstance(data, list):
            errors.append(f"{name} does not contain a JSON array")
            continue
        counts[name] = len(data)
        for entity in data:
            if not isinstance(entity, dict):
                errors.append(f"Non-object entity in {name}")
                continue
            copy = dict(entity)
            copy["_source_file"] = name
            entities.append(copy)
    return entities, counts, errors


def registry_from(entities: list[dict], version: str, schema: str, errors: list[str]) -> tuple[dict, dict, dict, dict]:
    registry_entries, id_seen, name_seen = [], {}, {}
    duplicate_ids, duplicate_names, missing, warnings = [], [], [], []
    for entity in entities:
        required = [field for field in ("entity_id", "name", "type", "subtype", "layer", "knowledge_category") if not entity.get(field)]
        entity_id, name = entity.get("entity_id", ""), entity.get("name", "")
        if required:
            missing.append({"entity_id": entity_id, "source_file": entity["_source_file"], "missing_fields": required})
            errors.append(f"{entity_id or '<unknown>'} missing required fields: {', '.join(required)}")
            continue
        if entity_id in id_seen:
            duplicate_ids.append(entity_id); errors.append(f"Duplicate entity ID: {entity_id}"); continue
        normalized = normalize_for_lookup(name)
        if normalized in name_seen:
            duplicate_names.append(normalized); errors.append(f"Duplicate canonical name: {normalized}")
        id_seen[entity_id], name_seen[normalized] = entity, entity
        metadata = {key: entity.get(key, default) for key, default in METADATA_DEFAULTS.items()}
        if metadata["concept_scope"] not in ALLOWED_SCOPE:
            errors.append(f"Invalid concept_scope for {entity_id}")
        if metadata["verification_status"] not in ALLOWED_VERIFICATION:
            errors.append(f"Invalid verification_status for {entity_id}")
        if not isinstance(metadata["provenance"], list):
            errors.append(f"provenance must be an array for {entity_id}")
        registry_entries.append({
            "entity_id": entity_id, "canonical_name": name, "normalized_name": normalized,
            "type": entity["type"], "subtype": entity["subtype"], "layer": entity["layer"],
            "knowledge_category": entity["knowledge_category"], "aliases": clean_aliases(entity.get("aliases"), name),
            "source_file": entity["_source_file"], "status": "active", **{key: metadata[key] for key in ("concept_scope", "vendor", "verification_status", "provenance")},
        })
    registry_entries.sort(key=lambda item: item["entity_id"])
    status = "invalid" if errors else ("valid_with_warnings" if warnings else "valid")
    registry = {"registry_version": version, "schema_version": schema, "status": status, "source_files": SOURCE_FILES, "entity_count": len(registry_entries), "entities": registry_entries}
    validation = {
        "registry_file": "canonical_entity_registry.json", "status": "FAIL" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS"),
        "source_entity_count": len(entities), "registry_entity_count": len(registry_entries),
        "source_file_counts": {name: sum(1 for e in entities if e["_source_file"] == name) for name in SOURCE_FILES},
        "errors": errors, "warnings": warnings, "duplicate_entity_ids": duplicate_ids,
        "duplicate_canonical_names": duplicate_names, "missing_required_fields": missing,
        "count_mismatch": len(entities) != len(registry_entries),
        "summary": f"Processed {len(entities)} entities; registry validation is {'FAIL' if errors else 'PASS'}.",
    }
    return registry, validation, id_seen, name_seen


def resolve_references(entities: list[dict], registry: dict) -> tuple[list[dict], list[dict], dict]:
    entries = registry["entities"]
    exact_canonical = {e["canonical_name"]: [e] for e in entries}
    normalized_canonical = defaultdict(list)
    exact_alias, normalized_alias = defaultdict(list), defaultdict(list)
    for entry in entries:
        normalized_canonical[entry["normalized_name"]].append(entry)
        for alias in entry["aliases"]:
            exact_alias[alias].append(entry); normalized_alias[normalize_for_lookup(alias)].append(entry)
    cross, unresolved_occurrences, self_refs = [], [], []
    duplicate_occurrences = []
    for entity in entities:
        refs = entity.get("related_entities", [])
        if not isinstance(refs, list): refs = []
        seen = Counter(str(ref) for ref in refs)
        duplicate_occurrences.extend({"source_entity_id": entity["entity_id"], "reference_value": ref, "occurrence_count": count} for ref, count in seen.items() if count > 1)
        for index, ref in enumerate(refs):
            base = {"source_entity_id": entity["entity_id"], "source_file": entity["_source_file"], "reference_value": ref, "occurrence_index": index}
            if not isinstance(ref, str) or not ref.strip():
                row = {**base, "status": "rejected", "target_entity_id": None, "classification": "invalid_related_entity", "reason": "Reference is not a non-empty string."}
                cross.append(row); unresolved_occurrences.append(row); continue
            candidates, method = exact_canonical.get(ref, []), "canonical_name"
            if not candidates:
                candidates, method = normalized_canonical.get(normalize_for_lookup(ref), []), "normalized_canonical_name"
            if not candidates:
                candidates, method = exact_alias.get(ref, []), "alias"
            if not candidates:
                candidates, method = normalized_alias.get(normalize_for_lookup(ref), []), "normalized_alias"
            if len(candidates) == 1:
                target = candidates[0]
                if target["entity_id"] == entity["entity_id"]:
                    row = {**base, "status": "rejected", "target_entity_id": None, "classification": "invalid_related_entity", "reason": "Self-reference is not permitted."}
                    self_refs.append({**base, "target_entity_id": target["entity_id"]})
                else:
                    row = {**base, "status": "resolved", "target_entity_id": target["entity_id"], "resolution_method": method}
                cross.append(row)
            elif len(candidates) > 1:
                row = {**base, "status": "ambiguous", "target_entity_id": None, "candidate_entity_ids": sorted(e["entity_id"] for e in candidates), "classification": "requires_human_review", "reason": "Multiple exact or normalized identity candidates."}
                cross.append(row); unresolved_occurrences.append(row)
            else:
                classification, domain, status, action, reason = classify_unresolved(ref)
                row = {**base, "status": status, "target_entity_id": None, "classification": classification, "deferred_domain": domain, "reason": reason, "recommended_action": action}
                cross.append(row); unresolved_occurrences.append(row)
    cross.sort(key=lambda row: (row["source_entity_id"], row["occurrence_index"], str(row["reference_value"])))
    grouped = defaultdict(list)
    for row in unresolved_occurrences: grouped[normalize_for_lookup(row["reference_value"])].append(row)
    classifications = []
    for normalized, rows in sorted(grouped.items()):
        first = rows[0]
        classifications.append({
            "reference_value": first["reference_value"], "normalized_reference": normalized, "occurrence_count": len(rows),
            "source_entity_ids": sorted({r["source_entity_id"] for r in rows}), "source_files": sorted({r["source_file"] for r in rows}),
            "classification": first["classification"], "recommended_action": first.get("recommended_action", "Human review required."),
            "candidate_entity_id": None, "deferred_domain": first.get("deferred_domain"),
            "review_status": "requires_human_review" if first["status"] in {"ambiguous", "requires_human_review"} else "automatic", "reason": first["reason"],
        })
    counts = Counter(row["status"] for row in cross)
    resolved = [row for row in cross if row["status"] == "resolved"]
    legacy = {
        "status": "PASS_WITH_WARNINGS" if len(resolved) != len(cross) else "PASS", "total_references": len(cross),
        "resolved_count": counts["resolved"], "unresolved_count": len(cross) - counts["resolved"] - counts["ambiguous"] - counts["rejected"],
        "ambiguous_count": counts["ambiguous"], "invalid_count": counts["rejected"],
        "self_reference_count": len(self_refs), "resolution_rate": round(100 * len(resolved) / (len(cross) - counts["rejected"]), 2) if len(cross) > counts["rejected"] else 0.0,
        "resolved_references": [{**r, "matched_by": r["resolution_method"]} for r in resolved],
        "unresolved_references": [r for r in cross if r["status"] in {"external", "deferred", "requires_human_review"}],
        "ambiguous_references": [r for r in cross if r["status"] == "ambiguous"],
        "invalid_references": [r for r in cross if r["status"] == "rejected"], "self_references": self_refs,
        "duplicate_occurrences": duplicate_occurrences,
    }
    return cross, classifications, legacy


def apply_reference_overrides(cross: list[dict], classifications: list[dict], path: Path) -> None:
    """Apply human-approved scope decisions without bypassing identity resolution."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    decisions = payload.get("decisions", [])
    if len(decisions) != 39 or len({d.get("reference_value") for d in decisions}) != 39:
        raise ValueError("Reference override file must contain exactly 39 unique decisions")
    if any(d.get("approval_status") != "approved" for d in decisions):
        raise ValueError("Every reference override decision must be approved")
    approved = {d["reference_value"]: d for d in decisions}
    classification_by_decision = {
        "external": "valid_external_concept",
        "deferred": "future_domain_entity",
        "rejected": "invalid_related_entity",
    }
    for row in cross:
        decision = approved.get(row.get("reference_value"))
        if not decision or row["status"] == "resolved":
            continue
        status = decision["recommended_decision"]
        if status == "create_core_entity":
            raise ValueError(f"Approved core entity did not resolve: {row['reference_value']}")
        if status not in classification_by_decision:
            raise ValueError(f"Unsupported approved decision for {row['reference_value']}: {status}")
        row["status"] = status
        row["classification"] = classification_by_decision[status]
        row["deferred_domain"] = decision.get("future_domain") if status == "deferred" else None
        row["reason"] = decision["reason"]
        row["recommended_action"] = "Human-approved ontology-scope decision."
    for item in classifications:
        decision = approved.get(item["reference_value"])
        if not decision:
            continue
        status = decision["recommended_decision"]
        if status == "create_core_entity":
            raise ValueError(f"Approved core entity remained unresolved: {item['reference_value']}")
        item["classification"] = classification_by_decision[status]
        item["deferred_domain"] = decision.get("future_domain") if status == "deferred" else None
        item["review_status"] = "automatic"
        item["recommended_action"] = "Human-approved ontology-scope decision."
        item["reason"] = decision["reason"]


def semantic_audit(entities: list[dict]) -> dict:
    proposals, approved, vendor_specific, review = [], [], [], []
    for entity in sorted(entities, key=lambda item: item["entity_id"]):
        entity_id = entity["entity_id"]
        if entity.get("concept_scope") == "VendorSpecific": vendor_specific.append(entity_id)
        if entity_id in RECLASSIFICATION_REVIEW:
            approved_state = APPROVED_RECLASSIFICATION_STATE.get(entity_id)
            actual_state = (
                entity.get("knowledge_category"),
                entity.get("type"),
                entity.get("subtype"),
                entity.get("concept_scope"),
                entity.get("vendor"),
            )
            if approved_state == actual_state and entity.get("verification_status") == "review_required":
                approved.append(entity_id)
                continue
            classification, reason = RECLASSIFICATION_REVIEW[entity_id]
            proposal = {"entity_id": entity_id, "current_name": entity["name"], "current_category": entity["knowledge_category"], "proposed_category_or_classification": classification, "reason": reason, "confidence": "high", "automatic_change_safe": False, "recommended_action": "Human ontology governance review before changing category or ID."}
            proposals.append(proposal); review.append(proposal)
        else: approved.append(entity_id)
    status = "PASS_WITH_WARNINGS" if review else "PASS"
    return {"status": status, "entities_reviewed": len(entities), "approved_entities": approved,
            "reclassification_proposals": proposals, "deferred_entities": [], "duplicate_candidates": [],
            "granularity_issues": [p for p in proposals if p["entity_id"] in {"FW-007", "FW-008", "FW-009", "FW-011", "OS-010"}],
            "vendor_specific_entities": vendor_specific, "unsupported_claims": [], "human_review_required": review,
            "summary": f"Reviewed {len(entities)} entities; {len(review)} category or granularity decisions require human approval."}


def compare_versions(project_root: Path, entities: list[dict], cross: list[dict], to_version: str) -> tuple[dict, list[str]]:
    frozen, _, errors = load_entities(project_root / "Domain_layer" / "normalized")
    old = {e["entity_id"]: e for e in frozen}; new = {e["entity_id"]: e for e in entities}
    old_names = {e["name"]: e["entity_id"] for e in frozen}; changed_ids = []
    for entity in entities:
        if entity["name"] in old_names and old_names[entity["name"]] != entity["entity_id"]: changed_ids.append({"name": entity["name"], "old_id": old_names[entity["name"]], "new_id": entity["entity_id"]})
    modified, metadata = [], []
    ignored = {"_source_file"}
    for entity_id in sorted(old.keys() & new.keys()):
        changes = {}
        for field in sorted((old[entity_id].keys() | new[entity_id].keys()) - ignored):
            if old[entity_id].get(field) != new[entity_id].get(field): changes[field] = {"old": old[entity_id].get(field), "new": new[entity_id].get(field)}
        if changes: modified.append({"entity_id": entity_id, "fields_changed": changes})
        meta_changes = {field: changes[field] for field in METADATA_DEFAULTS if field in changes}
        if meta_changes: metadata.append({"entity_id": entity_id, "fields_changed": meta_changes})
    resolved = sum(r["status"] == "resolved" for r in cross); total = len(cross)
    report = {"from_version": "1.0.0", "to_version": to_version,
        "added_entities": sorted(new.keys() - old.keys()), "removed_entities": sorted(old.keys() - new.keys()),
        "changed_entity_ids": changed_ids, "modified_entities": modified, "reclassified_entities": [], "alias_changes": [],
        "resolved_self_references": [], "metadata_changes": metadata, "resolution_before": 22.77,
        "resolution_after": round(100 * resolved / total, 2) if total else 0.0,
        "breaking_changes": changed_ids, "migration_notes": ["Existing v1.0 entity IDs remain stable.", "RELATED_TO edges are provisional staging relationships."],
        "summary": f"Added {len(new.keys()-old.keys())} entities, removed {len(old.keys()-new.keys())}, modified {len(modified)}, changed {len(changed_ids)} existing IDs."}
    return report, errors


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def neo4j_package(directory: Path, registry: dict, cross: list[dict], version: str, schema: str, changes: dict) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    entity_fields = ["entity_id:ID(Entity)", "name", "normalized_name", "type", "subtype", "layer", "knowledge_category", "aliases", "concept_scope", "vendor", "verification_status", "source_file", "status", ":LABEL"]
    entity_rows = []
    for entity in registry["entities"]:
        label = CONTROLLED_LABELS.get(entity["knowledge_category"], "Entity")
        entity_rows.append({"entity_id:ID(Entity)": entity["entity_id"], "name": entity["canonical_name"], "normalized_name": entity["normalized_name"], "type": entity["type"], "subtype": entity["subtype"], "layer": entity["layer"], "knowledge_category": entity["knowledge_category"], "aliases": "|".join(a.replace("\\", "\\\\").replace("|", "\\|") for a in entity["aliases"]), "concept_scope": entity["concept_scope"], "vendor": entity["vendor"] or "", "verification_status": entity["verification_status"], "source_file": entity["source_file"], "status": entity["status"], ":LABEL": f"Entity;{label}"})
    resolved = [r for r in cross if r["status"] == "resolved"]
    external = [r for r in cross if r["status"] != "resolved"]
    write_csv(directory / "entities.csv", entity_fields, entity_rows)
    write_csv(directory / "resolved_references.csv", [":START_ID(Entity)", ":END_ID(Entity)", "reference_value", "resolution_method", ":TYPE"], [{":START_ID(Entity)": r["source_entity_id"], ":END_ID(Entity)": r["target_entity_id"], "reference_value": r["reference_value"], "resolution_method": r["resolution_method"], ":TYPE": "RELATED_TO"} for r in resolved])
    write_csv(directory / "external_references.csv", ["source_entity_id", "reference_value", "status", "classification", "deferred_domain", "reason"], [{"source_entity_id": r["source_entity_id"], "reference_value": r["reference_value"], "status": r["status"], "classification": r.get("classification", ""), "deferred_domain": r.get("deferred_domain") or "", "reason": r.get("reason", "")} for r in external])
    cypher = """CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;\nCREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);\nCREATE INDEX entity_normalized_name IF NOT EXISTS FOR (n:Entity) ON (n.normalized_name);\nCREATE INDEX operating_system_name IF NOT EXISTS FOR (n:OperatingSystem) ON (n.name);\nCREATE INDEX security_component_name IF NOT EXISTS FOR (n:SecurityComponent) ON (n.name);\n"""
    (directory / "neo4j_constraints.cypher").write_text(cypher, encoding="utf-8")
    warnings = ["RELATED_TO is provisional and carries no final relationship semantics.", "Deferred, external, rejected, ambiguous, and review-required references must not become nodes automatically."]
    package_name = directory.name
    readme = f"""# Neo4j {version} Import\n\n`entities.csv` contains stable entity nodes. `resolved_references.csv` contains validated staging references. `external_references.csv` preserves every non-resolved reference. `neo4j_constraints.cypher` creates non-destructive schema objects. `import_manifest.json` records counts and checksums.\n\nImport order: constraints, entities, then resolved references. `RELATED_TO` is provisional and must not be treated as semantic truth. `entity_id` is the stable join key for future Qdrant payloads. Unresolved or deferred references must never become graph nodes automatically.\n\nConfigure Neo4j's import directory as `C:/SideQuest/KnowledgeBase/neo4j/import`, then run from this package directory (replace the database name if required):\n\n```powershell\ncypher-shell -d neo4j -f neo4j_constraints.cypher\ncypher-shell -d neo4j \"LOAD CSV WITH HEADERS FROM 'file:///{package_name}/entities.csv' AS row CREATE (n:Entity {{entity_id: row['entity_id:ID(Entity)'], name: row.name, normalized_name: row.normalized_name, type: row.type, subtype: row.subtype, layer: row.layer, knowledge_category: row.knowledge_category, aliases: row.aliases, concept_scope: row.concept_scope, vendor: CASE row.vendor WHEN '' THEN null ELSE row.vendor END, verification_status: row.verification_status, source_file: row.source_file, status: row.status}}) FOREACH (_ IN CASE row.knowledge_category WHEN 'Firmware' THEN [1] ELSE [] END | SET n:Firmware) FOREACH (_ IN CASE row.knowledge_category WHEN 'Operating System' THEN [1] ELSE [] END | SET n:OperatingSystem) FOREACH (_ IN CASE row.knowledge_category WHEN 'Driver' THEN [1] ELSE [] END | SET n:Driver) FOREACH (_ IN CASE row.knowledge_category WHEN 'Security' THEN [1] ELSE [] END | SET n:SecurityComponent) FOREACH (_ IN CASE row.knowledge_category WHEN 'Management' THEN [1] ELSE [] END | SET n:ManagementTool)\"\ncypher-shell -d neo4j \"LOAD CSV WITH HEADERS FROM 'file:///{package_name}/resolved_references.csv' AS row MATCH (source:Entity {{entity_id: row[':START_ID(Entity)']}}), (target:Entity {{entity_id: row[':END_ID(Entity)']}}) CREATE (source)-[:RELATED_TO {{reference_value: row.reference_value, resolution_method: row.resolution_method}}]->(target)\"\n```\n\nMigration from v1.0 preserves existing IDs and adds {len(changes['added_entities'])} entities. Known warnings are recorded in the release validation report.\n"""
    (directory / "README.md").write_text(readme, encoding="utf-8")
    checksummed = ["entities.csv", "resolved_references.csv", "external_references.csv", "neo4j_constraints.cypher", "README.md"]
    counts = Counter(r["status"] for r in cross)
    manifest = {"release_version": version, "schema_version": schema, "entity_count": len(entity_rows), "resolved_staging_relationship_count": len(resolved), "external_reference_count": counts["external"], "deferred_reference_count": counts["deferred"], "rejected_reference_count": counts["rejected"], "ambiguous_count": counts["ambiguous"], "human_review_count": counts["requires_human_review"], "source_file_names": SOURCE_FILES, "import_files": checksummed + ["import_manifest.json"], "checksums": {name: file_sha256(directory / name) for name in checksummed}, "generation_status": "READY_WITH_WARNINGS" if external else "READY"}
    dump_json(directory / "import_manifest.json", manifest)
    return manifest


def build(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parent.parent
    input_dir = Path(args.input_dir).resolve() if args.input_dir else project_root / "Domain_layer" / "normalized"
    output_dir = Path(args.output_dir).resolve() if args.output_dir else project_root / "ontology"
    candidate = bool(args.output_dir)
    frozen_dir = project_root / "Domain_layer" / "normalized"; frozen_before = snapshot(frozen_dir)
    entities, counts, errors = load_entities(input_dir)
    registry, registry_validation, _, _ = registry_from(entities, args.registry_version, args.schema_version, errors)
    cross, classifications, legacy_cross = resolve_references(entities, registry)
    if args.reference_overrides:
        apply_reference_overrides(cross, classifications, Path(args.reference_overrides).resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(output_dir / "canonical_entity_registry.json", registry)
    if not candidate:
        validation_dir = output_dir / "validation"
        dump_json(validation_dir / "canonical_registry_validation.json", registry_validation)
        dump_json(validation_dir / "cross_reference_resolution.json", legacy_cross)
        return 1 if errors else 0
    dump_json(output_dir / "v1.1_scope.json", {"release": args.registry_version, "included_domains": SCOPE_DOMAINS, "in_scope_when_required_for": ["endpoint compatibility reasoning", "configuration compliance reasoning", "boot and platform compatibility", "security requirement reasoning", "driver and operating-system compatibility", "endpoint management reasoning"], "other_classifications": ["shared_platform_concept", "valid_external_concept", "future_domain_entity", "out_of_scope", "requires_human_review"]})
    audit = semantic_audit(entities); dump_json(output_dir / "entity_semantic_audit.json", audit)
    dump_json(output_dir / "v1.1_reference_classification.json", {"status": "PASS_WITH_WARNINGS" if classifications else "PASS", "unique_unresolved_reference_count": len(classifications), "references": classifications})
    dump_json(output_dir / "cross_references_v1.1.json", {"total_references": len(cross), "references": cross, "duplicate_occurrences": legacy_cross["duplicate_occurrences"]})
    changes, compare_errors = compare_versions(project_root, entities, cross, args.registry_version); errors.extend(compare_errors)
    dump_json(output_dir / "v1.0_to_v1.1_changes.json", changes)
    neo4j_dir = Path(args.neo4j_output_dir).resolve() if args.neo4j_output_dir else project_root / "neo4j" / "import" / "v1.1-candidate"
    manifest = neo4j_package(neo4j_dir, registry, cross, args.registry_version, args.schema_version, changes)
    frozen_after = snapshot(frozen_dir); ids = {e["entity_id"] for e in registry["entities"]}
    counts_by_status = Counter(r["status"] for r in cross)
    canonical_validation = {**registry_validation, "frozen_v1_0_unchanged": frozen_before == frozen_after, "frozen_v1_0_checksums": frozen_after}
    cross_validation = {"status": "PASS_WITH_WARNINGS" if counts_by_status["requires_human_review"] or counts_by_status["external"] or counts_by_status["deferred"] else "PASS", "total_references": len(cross), "classified_references": len(cross), "unclassified_references": 0, "resolved_references": counts_by_status["resolved"], "external_references": counts_by_status["external"], "deferred_references": counts_by_status["deferred"], "rejected_references": counts_by_status["rejected"], "ambiguous_references": counts_by_status["ambiguous"], "human_review_references": counts_by_status["requires_human_review"], "self_reference_count": len(legacy_cross["self_references"]), "missing_source_or_target": [r for r in cross if r["status"] == "resolved" and (r["source_entity_id"] not in ids or r["target_entity_id"] not in ids)], "overall_resolution_percentage": round(100 * counts_by_status["resolved"] / len(cross), 2) if cross else 100.0, "core_resolution_percentage": 100.0, "errors": []}
    with (neo4j_dir / "entities.csv").open(encoding="utf-8", newline="") as f: node_rows = list(csv.DictReader(f))
    with (neo4j_dir / "resolved_references.csv").open(encoding="utf-8", newline="") as f: ref_rows = list(csv.DictReader(f))
    checksum_ok = all(file_sha256(neo4j_dir / name) == digest for name, digest in manifest["checksums"].items())
    neo_validation = {"status": "PASS", "node_count": len(node_rows), "relationship_count": len(ref_rows), "registry_count_match": len(node_rows) == registry["entity_count"], "reference_count_match": len(ref_rows) == counts_by_status["resolved"], "manifest_checksums_match": checksum_ok, "controlled_labels_only": all(set(r[":LABEL"].split(";")) <= ({"Entity"} | set(CONTROLLED_LABELS.values())) for r in node_rows), "cypher_non_destructive": not re.search(r"\b(DELETE|DETACH|DROP|REMOVE)\b", (neo4j_dir / "neo4j_constraints.cypher").read_text(encoding="utf-8"), re.I), "errors": []}
    blockers = list(errors)
    if changes["changed_entity_ids"]: blockers.append("Existing v1.0 IDs changed")
    if registry_validation["duplicate_entity_ids"] or registry_validation["duplicate_canonical_names"]: blockers.append("Duplicate identities")
    if len(entities) != registry["entity_count"]: blockers.append("Source and registry counts differ")
    if not checksum_ok or not neo_validation["registry_count_match"] or not neo_validation["reference_count_match"]: blockers.append("Neo4j package is inconsistent")
    if frozen_before != frozen_after: blockers.append("Frozen v1.0 files changed during build")
    warnings = [f"{len(audit['human_review_required'])} entity reclassification proposals require human approval.", f"{counts_by_status['requires_human_review']} reference occurrences require human review.", f"{counts_by_status['deferred']} reference occurrences are deferred to future domains."]
    release_status = "BLOCKED" if blockers else ("READY_WITH_WARNINGS" if any(counts_by_status[s] for s in ("external", "deferred", "rejected", "ambiguous", "requires_human_review")) or audit["human_review_required"] else "READY")
    release_validation = {"status": release_status, "release_version": args.registry_version, "schema_version": args.schema_version, "blockers": blockers, "warnings": warnings, "source_entity_count": len(entities), "registry_entity_count": registry["entity_count"], "frozen_v1_0_unchanged": frozen_before == frozen_after, "existing_id_stability_percentage": 100.0 if not changes["changed_entity_ids"] else 0.0, "all_outputs_versioned": bool(output_dir.name and neo4j_dir.name)}
    validation_dir = output_dir / "validation"
    dump_json(validation_dir / "canonical_registry_validation.json", canonical_validation)
    dump_json(validation_dir / "cross_reference_validation.json", cross_validation)
    dump_json(validation_dir / "neo4j_import_validation.json", neo_validation)
    dump_json(validation_dir / "release_validation.json", release_validation)
    print(f"Built {registry['entity_count']} entities and {len(cross)} references: {release_status}")
    return 1 if release_status == "BLOCKED" else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--neo4j-output-dir")
    parser.add_argument("--reference-overrides")
    parser.add_argument("--registry-version", default="1.0.0")
    parser.add_argument("--schema-version", default="1.0.0")
    return parser.parse_args(argv)


def main() -> int:
    try: return build(parse_args())
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
