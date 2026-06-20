# Relationship Record Schema Guide

## Purpose

`relationship_record.schema.json` defines the common JSON structure for future Knowledge Base relationship assertions. It is a structural contract only. It does not create production relationships, register predicates, convert Neo4j `RELATED_TO` staging edges, or make compatibility claims.

The schema uses JSON Schema Draft 2020-12 and has the stable identifier `urn:sidequest:knowledgebase:schema:relationship-record:1.0.0`.

## Record Fields

| Field | Meaning |
|---|---|
| `relationship_id` | Stable, globally unique identifier beginning with `REL-`. |
| `source_id` | Canonical entity ID at the relationship origin. |
| `relationship_type` | Uppercase controlled predicate identifier. Registration is checked later. |
| `target_id` | Canonical entity ID at the relationship destination. |
| `statement` | Human-readable wording of one assertion. |
| `assertion_scope` | Declares whether the assertion is universal or constrained. |
| `condition_logic` | Says whether all (`ALL`) or any (`ANY`) conditions must hold. |
| `conditions` | Structured, non-executable constraints on the assertion. |
| `evidence` | Sources supporting the assertion. Candidate records may use an empty array. |
| `confidence` | Numeric assessment from `0.0` through `1.0`. It is not approval. |
| `verification_status` | State of source/evidence verification. |
| `approval_status` | Governance lifecycle state of the relationship record. |
| `approved_by` | Approver identity; mandatory and non-empty for approved records. |
| `approved_at` | Approval date-time; mandatory and valid for approved records. |
| `source_release` | Entity release against which the assertion was authored. |
| `relationship_ontology_version` | Version of the relationship ontology contract. |
| `metadata` | Creation and maintenance bookkeeping, not relationship semantics. |

All top-level fields are required. Undeclared top-level fields are rejected.

## Verification and Approval

`verification_status` describes evidence review:

- `unverified`: no review has been completed.
- `review_required`: queued for evidence review.
- `source_verified`: supporting source material has been checked.
- `human_approved`: a human reviewer has verified the assertion.

`approval_status` describes governance state:

- `candidate`: proposed but not approved.
- `approved`: accepted through governance.
- `rejected`: reviewed and declined.
- `deprecated`: previously used but no longer current.

These dimensions are separate. An approved record must have `verification_status` equal to `source_verified` or `human_approved`, a non-empty `approved_by`, and a valid date-time in `approved_at`. Candidate, rejected, and deprecated records may leave approval fields null.

## Assertion Scope

- `universal`: asserted without record-level conditions; `conditions` may be empty.
- `conditional`: valid only when its explicit conditions hold.
- `version_specific`: constrained to one or more version conditions.
- `platform_specific`: constrained to a platform condition.
- `vendor_specific`: constrained to a vendor condition.

Every non-universal scope requires at least one condition. `condition_logic` remains required even when a universal record has no conditions.

## Conditions

Each condition contains `attribute`, `operator`, and `value`. Optional `unit` and `description` fields clarify interpretation. Unknown fields are rejected.

Allowed operators are `equals`, `not_equals`, `greater_than`, `greater_than_or_equal`, `less_than`, `less_than_or_equal`, `in`, `not_in`, `exists`, and `matches`. `in` and `not_in` require a non-empty array in this schema. Values may otherwise be strings, numbers, booleans, null, or arrays containing strings, numbers, and booleans. Object values and executable expressions are not allowed.

With `ALL`, every condition must hold. With `ANY`, one or more conditions must hold. The future evaluator, not JSON Schema, will execute that logic.

## Evidence

Evidence can point to official documentation, industry standards, vendor documentation, internal policy, user-provided documents, ingested documents, Knowledge Base sources, or manual review. Every item requires a non-empty `title` and controlled `source_type`. A URI is optional because evidence may be an ingested local PDF referenced by `source_id` and `locator`.

Candidate relationships may have an empty `evidence` array so extraction and review workflows can create structurally valid proposals without fabricating sources. Approval still requires governance. Predicate-specific evidence requirements will be defined later in relationship rules and enforced by the future validator.

## Metadata

Metadata requires `created_by`, `created_at`, `updated_at`, and `notes`. `created_by` must be non-empty. Timestamps may be null or valid date-time strings. Examples use null metadata timestamps so schema samples do not change over time.

## Neo4j Identity

`source_id` and `target_id` use the same stable `entity_id` carried by the canonical registry and Neo4j `Entity` nodes. A future importer can match endpoints by `Entity.entity_id`; the schema itself cannot query Neo4j or the registry.

Inverse edges should not be manually duplicated. A future relationship-type registry will define inverse behavior, and the validator or graph materialization process will create or check inverses consistently. Manual duplication risks divergent confidence, evidence, approval, and condition data.

## What JSON Schema Enforces

- Required fields and property types.
- No undeclared properties at the record, condition, evidence, or metadata level.
- Identifier, predicate, attribute, and version string shapes.
- Controlled enums.
- Confidence range.
- Condition value types and allowed operators.
- At least one condition for every non-universal scope.
- Approver, approval time, and verified status for approved records.
- Date-time and URI syntax when those values are present and a format checker is enabled.

## What the Future Python Validator Must Enforce

- `source_id` and `target_id` exist in the selected canonical registry.
- Source and target are different.
- `relationship_type` is registered in the future `relationship_types.json`.
- Predicate domain and range are permitted.
- `relationship_id` is globally unique.
- Duplicate source-type-target edges are detected.
- Evidence rules and confidence thresholds for each predicate are satisfied.
- Inverse relationships are consistent.
- Contradictions are detected.
- Condition attributes and units are registered and semantically valid.
- Statements contain one assertion and agree with structured endpoints and predicate.

These checks require external data or semantic reasoning and are intentionally not approximated with fragile schema tricks.

## Complete Candidate Example

This is synthetic test data, not a production assertion:

```json
{
  "relationship_id": "REL-EXAMPLE-001",
  "source_id": "TEST-SOURCE-001",
  "relationship_type": "EXAMPLE_LINK",
  "target_id": "TEST-TARGET-001",
  "statement": "Synthetic source links to synthetic target for schema demonstration only.",
  "assertion_scope": "universal",
  "condition_logic": "ALL",
  "conditions": [],
  "evidence": [],
  "confidence": 0.5,
  "verification_status": "review_required",
  "approval_status": "candidate",
  "approved_by": null,
  "approved_at": null,
  "source_release": "1.1",
  "relationship_ontology_version": "1.0.0",
  "metadata": {
    "created_by": "schema_example",
    "created_at": null,
    "updated_at": null,
    "notes": "Synthetic schema example only."
  }
}
```

## Complete Approved Conditional Example

This is synthetic test data with synthetic manual-review evidence:

```json
{
  "relationship_id": "REL-EXAMPLE-003",
  "source_id": "TEST-SOURCE-003",
  "relationship_type": "EXAMPLE_LINK",
  "target_id": "TEST-TARGET-003",
  "statement": "Synthetic source links to synthetic target under an approved example condition.",
  "assertion_scope": "conditional",
  "condition_logic": "ANY",
  "conditions": [
    {
      "attribute": "example_platform",
      "operator": "in",
      "value": ["test_platform_a", "test_platform_b"],
      "unit": null,
      "description": "Synthetic condition for schema demonstration only."
    }
  ],
  "evidence": [
    {
      "evidence_id": "EVID-EXAMPLE-001",
      "source_type": "manual_review",
      "source_id": "TEST-DOC-001",
      "title": "Synthetic schema example review",
      "locator": "Example section",
      "notes": "Schema example only; not production evidence."
    }
  ],
  "confidence": 0.9,
  "verification_status": "human_approved",
  "approval_status": "approved",
  "approved_by": "schema_example_reviewer",
  "approved_at": "2000-01-01T00:00:00Z",
  "source_release": "1.1.0-rc2",
  "relationship_ontology_version": "1.0.0",
  "metadata": {
    "created_by": "schema_example",
    "created_at": null,
    "updated_at": null,
    "notes": "Synthetic schema example only; not a production relationship."
  }
}
```

## Invalid Examples

The following fragments are intentionally incomplete and invalid.

### Unknown Field

```json
{"unexpected_property": true}
```

Rejected because `additionalProperties` is false.

### Empty Statement

```json
{"statement": ""}
```

Rejected because a statement must contain at least ten characters and a non-whitespace character.

### Confidence Above One

```json
{"confidence": 1.1}
```

Rejected because confidence must be between `0.0` and `1.0`.

### Conditional Scope Without Conditions

```json
{"assertion_scope": "conditional", "conditions": []}
```

Rejected by the scope `if`/`then` rule, which requires at least one condition.

### Approved Without Approver

```json
{"approval_status": "approved", "approved_by": null, "approved_at": null}
```

Rejected because approved records require a non-empty approver, a valid approval date-time, and an approved verification status.

### Invalid Condition Operator

```json
{"attribute": "example_version", "operator": "execute", "value": "2.0"}
```

Rejected because `execute` is not an allowed condition operator. Conditions never contain executable code.
