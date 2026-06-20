# Ontology Versioning Guide

## Release Lifecycle

- **Draft:** Work in progress. Identity and meaning may still be reviewed; it is not a downstream dependency.
- **Candidate:** Complete proposed release undergoing validation and governance approval.
- **Approved:** Validated and approved for governed downstream use. The release is frozen in place.
- **Deprecated:** Retained and readable but discouraged for new use. A rationale and migration path are required.
- **Retired:** Historical identity retained; no new relationships or dependencies may target it without explicit historical-use policy.

Candidate status may return to Draft for remediation. Approval cannot skip Candidate validation. Approved content must pass through Deprecated before retirement.

## Version Numbers

Versions use `MAJOR.MINOR.PATCH`.

- `v1.0.0`: initial governed release.
- `v1.1.0`: backward-compatible additions such as new entities or predicates.
- `v1.1.1`: packaging, documentation, or validation correction without semantic change.
- `v2.0.0`: backward-incompatible semantic change requiring migration.

Increase MAJOR when predicate meaning/direction or other published semantics become incompatible. Increase MINOR for backward-compatible additions. Increase PATCH for non-semantic fixes.

## Immutability And Compatibility

Entity IDs and released canonical names never change. Published predicate direction and meaning remain stable within a major line. Frozen releases are never edited in place. Deprecated entities and predicates remain traceable, with replacement links and release notes where available.

Each package declares its exact entity registry and relationship ontology dependencies. The detailed rules are authoritative in `ontology/governance/ontology_version_policy.json` and `ontology/governance/ontology_lifecycle_policy.json`.
