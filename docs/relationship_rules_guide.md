# Relationship Rules Guide v1.0

## Purpose

`relationship_types.json` defines what each predicate means. `relationship_rules.json` defines where that predicate may be used and which integrity, review, approval, and import checks apply. This step creates validation policy only; it creates no relationship records and does not convert provisional `RELATED_TO` edges.

## Domain and Range

The **source domain** is the set of entity categories permitted at the source of a predicate. The **target range** is the set permitted at its target. Relationship Ontology v1.0 uses the registry's exact `knowledge_category` values as its primary constraint:

- `Driver`
- `Firmware`
- `Management`
- `Operating System`
- `Security`

These categories are stable and consistently populated in RC2. Entity `type` is narrower but still broad, so most rules use `derived_from_allowed_categories` with an empty `allowed_types` array. This means type validity follows category membership; it does not mean no type is permitted. Explicit type restrictions are used only where useful and stable, such as `ManagementTool` for the source of `MANAGES`, `SecurityComponent` for the source of `PROTECTS`, and `OperatingSystem` for `RUNS_ON` and `INSTALLED_ON` targets.

## Policy Fields

- `category_policy`: either an explicit category allowlist or any registered category.
- `type_policy`: explicit type allowlist, any registered type, or types derived from allowed categories.
- `requires_manual_review_for`: combinations that need governance attention. It does not override an allowlist error.
- `same_category_policy`: whether source and target may, must, must not, or should only after review share a category.
- `cross_category_policy`: whether cross-category use is allowed, forbidden, or reviewable.
- `self_relationship_allowed`: false for every predicate.
- `cycle_policy`: forbidden, review, or not applicable.
- `duplicate_policy`: exact duplicates are rejected.
- `reverse_edge_policy`: virtual inverses are never materialized.
- `evidence_policy`, `condition_policy`, `minimum_confidence`, `allowed_assertion_scopes`: copied without weakening from `relationship_types.json`.
- `production_import_requires_approval`: true for every predicate.
- Severity fields distinguish invalid combinations (`error`) from review combinations (`warning`).

## Domain/Range Matrix

`Any` means every registered category listed above.

| Predicate | Allowed source categories | Allowed target categories | Same category | Cross category | Cycle policy |
|---|---|---|---|---|---|
| `IS_A` | Any | Any | required | forbidden | forbidden |
| `IMPLEMENTS` | Driver, Firmware, Management, Operating System, Security | Any | allowed | allowed | not applicable |
| `PART_OF` | Any | Any | allowed | review | forbidden |
| `USES` | Any | Any | allowed | allowed | not applicable |
| `CONFIGURES` | Management, Security | Any | allowed | allowed | review |
| `ENABLES` | Any | Any | allowed | allowed | review |
| `INITIALIZES` | Firmware | Driver, Firmware, Operating System, Security | allowed | allowed | forbidden |
| `MANAGES` | Management | Any | allowed | allowed | review |
| `MONITORS` | Management, Security | Any | allowed | allowed | not applicable |
| `PROTECTS` | Security | Any | allowed | allowed | not applicable |
| `UPDATES` | Management | Any | allowed | allowed | forbidden |
| `DEPENDS_ON` | Any | Any | allowed | allowed | review |
| `INSTALLED_ON` | Driver, Management, Security | Operating System | forbidden | allowed | forbidden |
| `REQUIRES` | Any | Any | allowed | allowed | forbidden |
| `RUNS_ON` | Driver, Management, Security | Operating System | forbidden | allowed | forbidden |
| `DEPRECATED_BY` | Any | Any | required | forbidden | forbidden |
| `REPLACES` | Any | Any | required | forbidden | forbidden |
| `COMPATIBLE_WITH` | Any | Any | allowed | allowed | not applicable |
| `CONFLICTS_WITH` | Any | Any | allowed | allowed | not applicable |
| `SUPPORTS` | Driver, Firmware, Management, Operating System, Security | Driver, Firmware, Management, Operating System, Security | allowed | allowed | not applicable |

`RUNS_ON` is inherently cross-category in v1.0. Because `required` is not an allowed `cross_category_policy` value, it uses `allowed` while its explicit source and target allowlists permit only the specified cross-category direction.

## Rules by Category

### Taxonomic

`IS_A` requires source and target to share a category. Self-relationships, cross-category classification, duplicate edges, and cycles are errors. Multiple parents are allowed. Only `IS_A` is transitive, but transitive closure may be queried rather than stored as new approved assertions without provenance. Component-versus-subtype ambiguity is reviewed and may indicate `PART_OF`.

### Structural

- `PART_OF` permits same-category composition, reviews cross-category composition, forbids cycles, and is not transitively inferred.
- `IMPLEMENTS` permits broad registered source/target categories, but targets whose role as a specification, interface, standard, abstraction, or governed concept is unclear require review. External targets cannot be approved until modeled.
- `USES` permits registered categories in either position but requires direct functional use. It cannot stand in for `DEPENDS_ON` or `REQUIRES`.

### Functional

- `INITIALIZES` is sourced only from Firmware and targets Firmware, Operating System, Driver, or Security. Management targets are outside the v1.0 allowlist. Cycles are errors.
- `ENABLES` is broad but vague or reciprocal claims and cycles require review.
- `MANAGES` requires a Management source. Reciprocal management requires review.
- `MONITORS` permits Management or Security sources. Firmware, Operating System, and Driver sources require a future rule revision rather than automatic approval.
- `PROTECTS` requires a Security source and a concrete protection function.
- `CONFIGURES` permits Management and Security sources; Security use is reviewed where its configuration-enforcement role is uncertain.
- `UPDATES` requires a Management source and forbids self, reciprocal, and cyclic update claims.

### Dependency

- `REQUIRES` is broad but forbids cycles. Universal requirements require review, and authoritative evidence must establish mandatory status.
- `DEPENDS_ON` reviews cycles and never infers transitivity.
- `RUNS_ON` and `INSTALLED_ON` allow Driver, Security, or Management sources and require an Operating System target. They are distinct and neither implies compatibility or support.

### Lifecycle

`REPLACES` and `DEPRECATED_BY` require source and target to share a category. Both forbid cycles and reciprocal edges and require authoritative evidence. Newness does not prove replacement, and replacement alone does not prove formal deprecation.

### Compatibility

`SUPPORTS`, `COMPATIBLE_WITH`, and `CONFLICTS_WITH` always require conditions and authoritative evidence. They do not infer reverse edges. Universal or generic unscoped compatibility claims are not accepted under normal v1.0 policy. `RELATED_TO`, `RUNS_ON`, and `INSTALLED_ON` do not imply compatibility or official support.

## Duplicate Detection

An exact duplicate is identified by canonical comparison of:

1. `source_id`
2. `relationship_type`
3. `target_id`
4. `assertion_scope`
5. `conditions`

Condition objects are normalized deterministically so object-key order is ignored. Array order and meaning are preserved. No condition expression is executed. Exact duplicates are errors; separate assertions with different canonical scope or conditions are not automatically duplicates.

## Inherited Policies

Evidence policy, condition policy, minimum confidence, and allowed assertion scopes are copied from the registered relationship type. Rules may narrow domain/range use but must not weaken these inherited requirements.

- Recommended evidence permits candidates without making them production-ready.
- Required evidence must be present before approval.
- Authoritative evidence is mandatory for high-risk dependency, lifecycle, and compatibility predicates.
- Conditions follow `optional`, `required_when_non_universal`, or `always_required` from the type catalog.
- Confidence below the inherited minimum is an error.

## Errors and Warnings

Errors prevent approval and production import. They include missing endpoints, unknown predicates, self-relationships, invalid categories, forbidden category direction, missing evidence or conditions, low confidence, duplicates, forbidden cycles, approval inconsistency, and contradictory approved relationships.

Warnings permit candidate storage but block approval until reviewed. They include review combinations, review cycles, broad universal claims, overlapping scope, possible predicate confusion, and reciprocal non-symmetric relationships.

## Cross-Predicate Constraints

Seven machine-readable constraints are defined:

1. Approved `COMPATIBLE_WITH` and `CONFLICTS_WITH` on the same direction, scope, and conditions are contradictory and rejected.
2. Overlapping `SUPPORTS` and `CONFLICTS_WITH` require human review.
3. Overlapping `REQUIRES` and `CONFLICTS_WITH` require human review.
4. `IS_A` and `PART_OF` on the same pair require review for predicate confusion.
5. `RUNS_ON` and `INSTALLED_ON` may coexist but automatic inference between them is prohibited.
6. Reciprocal `REPLACES` assertions form a forbidden cycle.
7. Reciprocal `DEPRECATED_BY` assertions form a forbidden cycle.

Predicates are not considered contradictory merely because they occur on the same entities under different conditions. Conditions and scope must be compared canonically or evaluated for overlap as specified by each constraint.

## Neo4j Import Policy

Semantic relationships may be imported only when:

- the predicate rule is enabled;
- `approval_status` is `approved`;
- source and target already exist;
- the relationship has no validation errors or warnings;
- the relationship ID is present;
- the canonical direction is used.

Candidate, rejected, and deprecated relationships are rejected from production import. Virtual inverses are not materialized. The Neo4j type comes from `relationship_type`. Provisional `RELATED_TO` staging edges are excluded from semantic releases. This step does not execute import commands.

## Examples of Rule Outcomes

These are category-level illustrations only, not relationship facts:

### Allowed

- A Management source using `MANAGES` toward an Operating System target, assuming all record, evidence, confidence, and approval checks pass.
- A Security source using `PROTECTS` toward a Firmware target with required evidence.
- A Driver source using `RUNS_ON` toward an Operating System target with required conditions.

### Rejected

- A Firmware source using `MANAGES`, because v1.0 permits only Management sources.
- A Management source using `RUNS_ON` toward a Firmware target, because the target must be Operating System.
- Cross-category `IS_A`, reciprocal `REPLACES`, any self-relationship, or an exact duplicate.
- A compatibility predicate without authoritative evidence and conditions.

### Manual Review

- Cross-category `PART_OF`.
- A broad universal `REQUIRES` assertion.
- Reciprocal `MANAGES`, `MONITORS`, `PROTECTS`, `CONFIGURES`, or `ENABLES` claims.
- Overlapping `SUPPORTS` and `CONFLICTS_WITH` scopes.
- An `IMPLEMENTS` target whose specification or abstraction role is unclear.

## Modeling Limitations

The five registry categories are intentionally broad. They cannot distinguish standards, interfaces, abstract capabilities, services, utilities, agents, policies, and products with the precision future rules may need. Type restrictions are therefore conservative. A future ontology version may introduce governed entity classifications and narrower domain/range rules, but this version does not invent them or mutate entities to satisfy constraints.

No actual relationships, candidate relationships, inverse edges, or Neo4j data are generated by this step.
