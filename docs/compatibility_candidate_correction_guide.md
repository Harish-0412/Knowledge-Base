# Compatibility Candidate Correction Guide

## Purpose

Phase 6 applies deterministic structural corrections to the 42 raw compatibility rule candidates extracted from `DOC-CA114A84AE60`. It does **not** approve, merge, invent, or delete candidates. Every change is recorded in a field-level trace, the raw source is never modified, and every source candidate must appear in exactly one lineage category.

---

## Inputs

| File | Role |
|---|---|
| `CompatibilityLayer/source/raw/normalized_rule_candidates.json` | Protected raw input (SHA-256 verified) |
| `ontology/releases/v1.1-rc2/canonical_entity_registry.json` | Entity resolution authority (58 entities) |
| `CompatibilityLayer/entity_resolution/resolved_entities.json` | Phase 3-4 resolution outcomes |

---

## Outputs

| File | Content |
|---|---|
| `rules/corrected/corrected_rule_candidates.json` | 43 corrected candidates (42 source + 1 split) |
| `rules/corrected/candidate_correction_trace.json` | Field-level trace of every change |
| `rules/corrected/candidate_split_merge_map.json` | Split, merge, one-to-one, and unconverted lineage |
| `rules/corrected/correction_report.json` | Accounting summary and correction type counts |
| `rules/corrected/clarification_queue.json` | 32 items requiring Phase 9 human review |

---

## Running Phase 6

```powershell
python scripts/correct_compatibility_candidates.py \
    --input CompatibilityLayer/source/raw/normalized_rule_candidates.json \
    --analysis-dir CompatibilityLayer/analysis \
    --resolution-dir CompatibilityLayer/resolution \
    --output-dir CompatibilityLayer/rules/corrected

# Dry run - validates without writing
python scripts/correct_compatibility_candidates.py \
    --input CompatibilityLayer/source/raw/normalized_rule_candidates.json \
    --output-dir CompatibilityLayer/rules/corrected \
    --dry-run

# Full rebuild (authoritative)
python build_phase6_7.py
```

---

## Safe Automatic Corrections

The following corrections are applied automatically when unambiguous:

| Correction Type | Example |
|---|---|
| `operator_normalization` | `>=` → `greater_than_or_equal` |
| `logic_normalization` | `AND` → `ALL`, `OR` → `ANY` |
| `version_normalization` | `v6.4.2` → `6.4.2` (raw preserved) |
| `component_type_normalization` | `BIOS` → `bios` |
| `entity_resolution` | `System BIOS` → `FW-001` |
| `exception_recovery` | Explicit source-text exceptions recovered (RCAND-000367) |
| `candidate_split` | RCAND-000365 OR-condition split into two lineage-linked candidates |

---

## Special Case Handling

### RCAND-000361 — Version Logic Inconsistency
Condition is firmware `8.1.x`; requirement is `>=6.4.2`. Since `8.1.x` already satisfies `>=6.4.2`, the threshold does not resolve the stated issue. **Routed to clarification** with reason `inconsistent_version_logic`. Not eligible for generation.

### RCAND-000365 — OR Condition Split
Source states "Platform Driver Pack 12.5.0 supports Enterprise OS 2025.2 and 2026.1." The OR logic is split into two lineage-linked `feature_support_added` candidates — one per OS version. Both are in the clarification queue (confidence 0.3, unverified_value tag).

### RCAND-000367 — Exception Recovery
Source explicitly exempts "ProBook Series, Enterprise Laptop Series, or ComputeNode Servers." Three exception records are recovered from the source excerpt. Device family entity IDs remain `null` (no Layer 2 product registry available). Rule stays in clarification until device families are resolved.

### RCAND-000368 — Optional Integration
Source says "tested-but-optional configuration." Connector is not modeled as a mandatory requirement. Routed to clarification with `optionality_unclear`.

### RCAND-000369 — Advisory Deferral
Source uses "may defer." Not converted to a mandatory requirement. Routed to clarification with `source_context_incomplete`.

### RCAND-000374, 376, 377, 382, 385, 400 — Unknown Applicability
Conditions contain literal `unknown`. Cannot recover applicability from remediation alone. All six routed to clarification with `unknown_applicability`.

### RCAND-000398 — Validation Checkpoint
"Reboot Cycle" is a post-update validation assertion, not a software component entity. Not modeled as a firmware version requirement. Routed to clarification with `rule_type_ambiguous`.

### RCAND-000401 — Procedural Reference
"Step 1" is a sequencing procedural reference, not a software component. Requirement routed to clarification.

---

## Accounting Invariant

All 42 source candidates must appear in exactly one of:

```
one_to_one  +  splits (source IDs)  +  unconverted  =  42
```

This invariant is asserted at runtime. Any violation causes a hard failure.

---

## Candidate Format

Every corrected candidate includes:

```json
{
  "candidate_id": "RCAND-000363",
  "original_candidate_hash": "<16-char hex>",
  "rule_type": "min_version_constraint",
  "condition_logic": "ALL",
  "conditions": [...],
  "requirements": [...],
  "exceptions": [],
  "remediation_hint": "...",
  "severity": "critical",
  "confidence_score": 1.0,
  "evidence_verification_status": "review_required",
  "corrections_applied": ["operator_normalization: ..."],
  "clarification_reasons": [],
  "eligible_for_rule_generation": true
}
```

No candidate may carry `approval_status=approved` or `evidence_verification_status=source_verified` in Phase 6.

---

## Tests

```powershell
python -m pytest tests/test_compatibility_candidate_correction.py -v
```

25 tests covering: raw immutability, SHA verification, 42-candidate accounting, operator/logic normalization, raw value preservation, determinism, trace completeness, split lineage, exception recovery, special-case handling, no-invented-entities, no-approval-status, no-source-verified.
