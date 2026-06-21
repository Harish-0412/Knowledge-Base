# Compatibility Rule Generation Guide

## Purpose

Phase 7 generates structured, unapproved Layer 3 candidate compatibility rules from the corrected candidates produced in Phase 6. Only candidates marked `eligible_for_rule_generation: true` are converted. All others are written to the clarification queue for Phase 9 human review.

This phase does **not** approve rules, import to Neo4j or Qdrant, or generate embeddings.

---

## Inputs

| File | Role |
|---|---|
| `rules/corrected/corrected_rule_candidates.json` | Phase 6 output (43 corrected candidates) |
| `CompatibilityLayer/ontology/` | Compatibility rule types, relationships, lifecycle |
| `ontology/releases/v1.1-rc2/canonical_entity_registry.json` | Entity ID validation (58 entities) |

---

## Outputs

| File | Content |
|---|---|
| `rules/candidate/compatibility_rule_candidates.json` | 11 generated candidate rules |
| `rules/candidate/candidate_rule_manifest.json` | Counts, distribution, artifacts, safety notice |
| `rules/candidate/candidate_generation_trace.json` | Per-rule generation trace |
| `rules/candidate/candidate_evidence_gaps.json` | Evidence gaps (missing excerpts etc.) |
| `rules/candidate/candidate_generation_report.json` | Summary report |
| `rules/needs_clarification/compatibility_rules_needing_clarification.json` | 32 items for Phase 9 |

---

## Running Phase 7

```powershell
python scripts/generate_compatibility_rules.py \
    --corrected-input CompatibilityLayer/rules/corrected/corrected_rule_candidates.json \
    --compatibility-ontology CompatibilityLayer/ontology \
    --domain-registry ontology/releases/v1.1-rc2/canonical_entity_registry.json \
    --output-dir CompatibilityLayer/rules/candidate \
    --clarification-dir CompatibilityLayer/rules/needs_clarification

# Dry run - validates outputs without writing
python scripts/generate_compatibility_rules.py \
    --corrected-input ... \
    --output-dir ... \
    --clarification-dir ... \
    --dry-run

# Full rebuild (authoritative - runs Phase 6 and 7 together)
python build_phase6_7.py
```

---

## Rule ID Generation

Rule IDs are deterministic 16-character hex hashes computed from a canonical JSON payload:

```python
hash_parts = {
    "source_candidate_ids": [...],
    "rule_type": "min_version_constraint",
    "subject_entity_id": "DRV-009",
    "object_entity_id": "OS-013",
    "condition_logic": "ALL",
    "conditions_normalized": [...],
    "requirements_normalized": [...],
    "exceptions": [...]
}
rule_id = "CRULE-" + sha256(canonical_json)[:16].upper() + "-001"
```

The same corrected input always produces the same rule ID. Timestamp and generation order are excluded.

---

## Rule Format

Every generated rule conforms to the compatibility rule schema and contains:

```json
{
  "rule_id": "CRULE-FBAB6E52A6005CC3-001",
  "source_candidate_ids": ["RCAND-000363"],
  "rule_type": "min_version_constraint",
  "subject": {
    "entity_id": "FW-001",
    "entity_name": "BIOS",
    "entity_kind": "Firmware",
    "resolution_status": "resolved_domain_entity"
  },
  "predicate": "REQUIRES",
  "object": {
    "entity_id": "FW-013",
    "entity_name": "System Firmware",
    "resolution_status": "resolved_domain_entity"
  },
  "outcome": "conditional",
  "assertion_scope": "version_specific",
  "condition_logic": "ALL",
  "conditions": [...],
  "requirements": [...],
  "exceptions": [],
  "remediation": [...],
  "evidence": [{
    "source_document_id": "DOC-CA114A84AE60",
    "source_excerpt": "System BIOS 6.4.2 requires System Firmware 8.2.0 or later.",
    "verification_status": "review_required"
  }],
  "approval_status": "candidate",
  "verification_status": "review_required",
  "production_import_allowed": false
}
```

---

## Rule-Type to Predicate Mapping

| Rule Type | Predicate | Outcome |
|---|---|---|
| `min_version_constraint` | `REQUIRES` | `conditional` |
| `known_issue_fixed` | `FIXED_BY` | `conditional` |
| `readiness_requirement` | `REQUIRES` | `conditional` |
| `feature_support_added` | `SUPPORTS` | `conditional` |
| `incompatible_combination` | `CONFLICTS_WITH` | `prohibited` |
| `update_order_constraint` | `BLOCKS` | `sequenced` |

---

## Generation Results (DOC-CA114A84AE60)

| Metric | Value |
|---|---|
| Source candidates | 42 |
| Corrected candidates | 43 (1 split) |
| Eligible for generation | 11 |
| Generated rules | 11 |
| Routed to clarification | 32 |
| Rules by type | min_version×4, readiness×4, incompatible×2, known_issue×1 |
| Rules by predicate | REQUIRES×8, CONFLICTS_WITH×2, FIXED_BY×1 |
| Production import allowed | **false** |

---

## Clarification Queue

32 candidates are routed to `rules/needs_clarification/` for Phase 9 review. Common reasons:

- `unknown_applicability` — conditions contain literal `unknown` (RCAND-000374, 376, 377, 382, 385, 400)
- `inconsistent_version_logic` — RCAND-000361 threshold does not resolve stated issue
- `rule_type_ambiguous` — RCAND-000398 validation checkpoint cannot be modeled as version requirement
- `optionality_unclear` — RCAND-000368 optional SIEM integration
- `source_context_incomplete` — RCAND-000369 advisory deferral, pending certification
- `ambiguous_condition_logic` — RCAND-000365 split (low confidence, unverified)

Clarification items include `known_facts`, `missing_facts`, `questions`, and `recommended_action` for reviewers.

---

## Safety Invariants

- `approval_status` is always `candidate`
- `verification_status` is always `review_required`
- `production_import_allowed` is always `false`
- No Neo4j or Qdrant writes occur
- No entity IDs are invented — all IDs validated against RC2 registry
- `RELATED_TO` predicate is forbidden
- Literal `unknown` entity names are forbidden in generated rules

---

## Phase 8 Inputs

The readiness report at `CompatibilityLayer/validation/phase6_7_readiness.json` lists the exact files Phase 8 should consume:

```json
"phase8_inputs": [
  "CompatibilityLayer/rules/candidate/compatibility_rule_candidates.json",
  "CompatibilityLayer/rules/candidate/candidate_rule_manifest.json",
  "CompatibilityLayer/rules/candidate/candidate_generation_trace.json"
]
```

---

## Tests

```powershell
python -m pytest tests/test_compatibility_rule_generation.py -v
```

27 tests covering: required fields, deterministic ID format, unique IDs, source lineage, subject/object resolution, no unknown entities, condition logic, version preservation, requirements, exceptions, remediation modality, evidence lineage, candidate status, review-required, rule types, registered predicates, no RELATED_TO, no invented IDs, clarification output counts, manifest counts, trace count, import disabled, no Neo4j/Qdrant outputs, dry-run immutability, payload count.
