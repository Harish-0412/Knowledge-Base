# Relationship Ontology Validator Guide

## Purpose

`scripts/validate_relationship_ontology.py` validates the Relationship Ontology v1.0 contract and its synthetic test fixtures. It reads the canonical RC2 registry and never creates entity or relationship knowledge.

## Commands

Run the ontology self-test:

```powershell
python scripts\validate_relationship_ontology.py ontology --output ontology\relationship_ontology\v1.0\validation\relationship_validator_self_test.json
```

Execute the fixture suite:

```powershell
python scripts\validate_relationship_ontology.py fixtures --output ontology\relationship_ontology\v1.0\validation\relationship_fixture_execution.json
```

Override inputs with `--release-dir` and `--registry`. A successful validation returns `0`; validation failure returns `2`; configuration or loading failure returns `3`.

## Validation Layers

The validator checks Draft 2020-12 schema constraints, registry endpoints, registered predicates, virtual inverse materialization, domain and range rules, evidence and condition policies, confidence thresholds, duplicates, cycles, contradictions, reciprocal assertions, and production approval policy.

Invalid fixtures pass only when independently calculated error codes include every expected code. Extra diagnostic codes are retained in the execution report rather than hidden.

## Production Safety

Fixtures are synthetic and test-only. Candidate, rejected, deprecated, or otherwise unapproved records fail production validation. `RELATED_TO` and virtual inverse labels are not registered semantic predicates. A passing fixture report does not authorize Neo4j import and does not establish factual evidence.
