# Reasoning Ontology Guide

## Purpose

The Reasoning Ontology is the vendor-neutral Layer 4 vocabulary for explaining why an enterprise endpoint state failed compatibility or compliance evaluation, how much risk it creates, what action can correct it, and what control can prevent recurrence.

It sits above:

- Layer 1 domain entities in `Domain_layer/normalized/`.
- Layer 3 compatibility rules and relationships in `CompatibilityLayer/ontology/`.

The Root Cause Engine, Recommendation Engine, Compliance Validator, and Llama Response Engine should use the stable IDs in this ontology. Display names are explanatory labels and are not reference keys.

## Ontology Structure

| Component | File | Purpose |
|---|---|---|
| Root causes | `ontology/root_cause_types.json` | Vendor-neutral explanation categories |
| Violations | `ontology/violation_types.json` | Classification of failed evaluations |
| Risks | `ontology/risk_levels.json` | Ordered impact and response model |
| Recommendations | `ontology/recommendation_types.json` | Corrective action categories |
| Preventions | `ontology/prevention_types.json` | Recurrence-reduction controls |
| Relationships | `ontology/reasoning_relationships.json` | Valid semantic edge types |
| Lifecycle | `ontology/reasoning_lifecycle.json` | Finding progression and valid transitions |
| Master ontology | `ontology/reasoning_ontology.json` | Integration metadata, grounding, counts, and reasoning policy |

JSON Schemas under `schemas/` define the component contracts. `validation/build_reasoning_ontology.py` deterministically generates and validates the ontology, and writes `validation/ontology_validation_report.json`.

## Reasoning Flow

1. Resolve inventory observations to Layer 1 entities.
2. Evaluate applicable Layer 3 rules, conditions, exceptions, version constraints, dependencies, conflicts, and update sequences.
3. Emit a violation when the rule's fail condition is met. Missing or contradictory evidence produces `RC-UNKNOWN-STATE`; it does not silently pass.
4. Classify one or more root causes using evidence and dependency traversal.
5. Assign risk from severity, business criticality, affected scope, exploitability, failure likelihood, dependency depth, evidence confidence, and remediation availability.
6. Rank applicable recommendations, retaining provenance to the originating rule and evidence.
7. Link prevention controls that reduce recurrence.
8. Apply remediation, re-evaluate the original rule, verify evidence, and resolve the finding.

For dependency chains, follow Layer 3 `DEPENDS_ON` and `REQUIRES` edges transitively with cycle detection. A dependent finding inherits the highest unresolved upstream risk; fleet scope or dependency depth may increase that risk.

## Entity Types

### Root Causes

Root causes answer *why* a violation occurred. A finding may have multiple causes, but each cause must be supported by evidence. `UnknownState` is the explicit outcome when evidence is insufficient.

### Violations

Violations answer *what kind of expectation failed*. Compatibility and compliance are broad classifications; dependency, version, lifecycle, security, policy, conflict, supportability, and upgrade types provide more precise downstream behavior.

### Risks

Risk levels are ordered: `Informational`, `Low`, `Medium`, `High`, and `Critical`. Risk is an assessment of a finding in context, not a fixed property of a violation type. The response-time text provides the default enterprise target and may be tightened by policy.

### Recommendations

Recommendations are action classes rather than executable vendor commands. An engine should resolve a class such as `REC-UPGRADE` into a concrete, evidence-backed plan for the target environment. Disruptive action requires sufficient evidence; `REC-MONITORING-ACTION` is preferred while the cause remains unknown.

### Preventions

Preventions are durable controls applied after or independently of remediation. Remediation removes the current condition; prevention reduces its likelihood of recurring.

## Relationships

- `CAUSES`: root cause to violation.
- `INDICATES`: evidence to root cause.
- `MITIGATED_BY`: root cause to recommendation.
- `PREVENTED_BY`: root cause to prevention.
- `ESCALATES_TO`: lower risk to higher risk.
- `DERIVED_FROM`: reasoning finding to Layer 3 compatibility rule.
- `TRIGGERS`: violation to reasoning finding.
- `REQUIRES_ACTION`: risk level to recommendation.
- `INCREASES_RISK`: violation to risk level.
- `REDUCES_RISK`: recommendation to residual risk level.

Relationships define allowed semantics. Instance edges must use canonical IDs, preserve evidence lineage, and comply with the declared source and target types.

## Lifecycle

The normal progression is:

```text
Detected -> Classified -> Analyzed -> RootCauseIdentified
  -> RecommendationGenerated -> RemediationPlanned
  -> RemediationApplied -> Verified -> Resolved
```

`Verified -> Analyzed` is the controlled re-analysis path when verification still fails. `RemediationApplied -> RemediationPlanned` permits a failed or partial remediation to be replanned. `Resolved` is terminal. Resolution requires verification evidence and a passing re-evaluation of the originating rule.

## Reasoning Example

```text
Firmware 3.2
  -> VersionViolation (VIOL-VERSION)
  -> Root Cause: VersionMismatch (RC-VERSION-MISMATCH)
  -> Risk: Critical
  -> Recommendation: Upgrade Firmware (REC-UPGRADE)
  -> Prevention: VersionValidation (PREV-VERSION-VALIDATION)
```

The engine must attach the Layer 3 rule and its evidence to justify the required version. `Critical` is appropriate only when context supports critical impact, such as unsafe operation, a critical vulnerability, or a blocking dependency chain.

## Extension Guidelines

1. Add a new concept only when existing types cannot represent meaning without ambiguity.
2. Keep identifiers stable, uppercase, unique, and names vendor-neutral. Never reuse a retired ID for a different meaning.
3. Add all inbound and outbound references in the same change. A root cause must be referenced by a violation, recommendation, or prevention; a recommendation must be reachable from a root cause.
4. Use the existing risk vocabulary. Add contextual factors to an assessment rather than creating product-specific risk levels.
5. For a relationship, declare valid source and target entity types and define one unambiguous direction.
6. For lifecycle changes, declare every new state and transition. Preserve an explicit initial state and at least one terminal state.
7. Update the builder, regenerate artifacts, and require `ontology_validation_report.json` to report `PASS` before release.
8. Treat Layer 1 entities and Layer 3 rules as external grounding. Do not copy vendor inventory or rule instances into the ontology taxonomy.

## Validation

Run from the project root:

```powershell
python ReasoningLayer/validation/build_reasoning_ontology.py
```

The command fails if it finds duplicate IDs, orphan entities, unresolved references, schema errors, invalid relationship endpoints, lifecycle inconsistencies, or master count mismatches.
