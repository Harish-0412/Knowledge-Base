# Future Extension Guide

## Expansion Principles

Layer 1 is the stable semantic foundation. Future layers reference its immutable entity IDs and governed predicates rather than copying or renaming concepts. New knowledge requires provenance, ownership, schema validation, lifecycle status, and versioned release packaging.

Extensions must not infer technical facts from names or fuzzy similarity, turn keywords into entities, import synthetic fixtures, or silently convert provisional `RELATED_TO` references into semantic assertions.

## Layer 2 Integration

Layer 2 introduces concrete product and inventory knowledge while referencing Layer 1 concepts:

- **Product Knowledge:** Product families, editions, versions, releases, components, and vendor lifecycle information.
- **Device Inventory:** Observed devices, installed software, firmware, drivers, configuration state, and collection timestamps.
- **Vendor Extensions:** Vendor-specific identifiers, catalogs, support matrices, advisories, and evidence locators.

Separate observed instances from canonical concepts. Inventory identifiers never replace ontology entity IDs. Vendor claims require authoritative vendor evidence and version/platform conditions.

## Layer 3 Compatibility Layer

Layer 3 stores evidence-backed `SUPPORTS`, `COMPATIBLE_WITH`, `CONFLICTS_WITH`, `REQUIRES`, and related assertions. Every assertion must use Relationship Ontology v1.0, explicit scope and conditions, authoritative evidence where required, confidence thresholds, human approval, and production validation.

## Layer 4 Compliance Layer

Layer 4 defines configuration baselines, policy requirements, evaluation rules, exceptions, and compliance results. It should distinguish desired configuration, observed state, evaluation outcome, and remediation guidance. Compliance history must be time-aware and auditable.

## Layer 5 Retrieval Layer

Layer 5 provides search and retrieval, including Qdrant or equivalent vector indexing. Vector payloads should carry stable entity or relationship IDs and source versions. Retrieval ranks evidence; it does not create ontology truth or bypass graph validation and governance.

## Ontology Expansion Strategy

1. Identify a bounded domain gap and its owning layer.
2. Search the canonical registry for exact canonical and alias matches.
3. Propose additions without changing existing IDs or canonical names.
4. Define category, type, subtype, scope, provenance, and lifecycle state.
5. Register any new predicate and its rules before using it.
6. Add positive and negative fixtures and focused tests.
7. Complete semantic review and governance approval.
8. Publish a new semantic version with change report, migration guidance, validation, and checksums.

Future-domain concepts currently deferred by RC2 should be introduced only when their domain model and governance package are ready. Layer-specific releases must declare the exact Layer 1 version they consume.
