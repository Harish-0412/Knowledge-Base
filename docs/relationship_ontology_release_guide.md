# Relationship Ontology v1.0 Release Guide

## Scope

Relationship Ontology v1.0 contains a Draft 2020-12 relationship-record schema, 20 controlled predicates, domain/range rules, test-only fixtures, a Python validator, deterministic release metadata, and governance documentation. It contains no approved production relationships and no Neo4j relationship import package.

`RELATED_TO` is excluded because it is a provisional staging label rather than governed semantic meaning. Virtual inverse labels are query conveniences and are not stored. Synthetic fixtures must never be imported.

## Layout

- `ontology/relationship_ontology/v1.0/`: schema, catalogs, rules, manifest, checksums, notes
- `ontology/relationship_ontology/v1.0/examples/`: test-only valid and invalid fixtures
- `ontology/relationship_ontology/v1.0/validation/`: Steps 4-7 reports
- `scripts/validate_relationship_ontology.py`: record and fixture validator
- `scripts/verify_relationship_ontology_release.py`: release builder and verifier
- `tests/test_relationship_validator.py`: focused validator tests
- `tests/test_relationship_ontology_release.py`: focused release tests

The manifest records scope, derived counts, policies, validation status, runtime requirements, artifact metadata, limitations, and the next phase. `artifact_checksums.json` hashes immutable release artifacts with SHA-256 using binary contents. Neither the manifest nor checksum file hashes itself.

## Build And Verify

```powershell
python scripts\verify_relationship_ontology_release.py build --release-dir ontology\relationship_ontology\v1.0 --registry ontology\releases\v1.1-rc2\canonical_entity_registry.json --release-version 1.0.0 --run-full-tests
python scripts\verify_relationship_ontology_release.py verify --release-dir ontology\relationship_ontology\v1.0 --registry ontology\releases\v1.1-rc2\canonical_entity_registry.json
```

Exit codes are `0` READY, `1` READY_WITH_WARNINGS, `2` validation-blocked, `3` configuration/dependency failure, `4` checksum or immutability failure, and `5` test failure.

READY requires all ten gates to pass. READY_WITH_WARNINGS permits only documented nonblocking warnings. BLOCKED indicates a missing artifact, validation failure, test failure, nondeterminism, mutation, checksum mismatch, dependency problem, or production-safety failure.

## Consumers And Safety

Candidate generators consume the controlled predicates and rules but must leave generated records in candidate status. Validators resolve source and target IDs only against the declared canonical registry. Neo4j importers must require `approval_status=approved` plus a production validation PASS; fixture or candidate reports are insufficient.

Compatibility, version, platform, and vendor claims require structured conditions and predicate-appropriate evidence. The validator checks evidence structure and policy, not factual truth. Human review remains mandatory.

## Versioning

Create v1.1 in a new version directory. Preserve existing predicate names, directions, and meanings. Add backward-compatible predicates or metadata in a minor release. To retire a predicate, mark it deprecated, document its replacement and migration path, and retain validation support for historical records before removal in a future major version.

Qdrant and retrieval integration remain separate because this release governs graph semantics and validation, not vector indexing. The next handoff is evidence-backed candidate generation, review, approval, production validation, and only then a separately governed Neo4j import.
