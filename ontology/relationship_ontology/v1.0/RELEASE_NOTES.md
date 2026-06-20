# Relationship Ontology v1.0 Release Notes

Version: `1.0.0`  
Entity registry: `1.1.0-rc2`  
Release status: `READY`

## Purpose

This release defines the relationship ontology and validator. It does not contain approved production relationship instances.

The release provides the relationship-record schema, 20 controlled predicates across Taxonomic, Structural, Functional, Dependency, Lifecycle, and Compatibility categories, one domain/range rule per predicate, synthetic valid and invalid fixtures, validator tooling, release verification, and governance documentation.

## Validation

- Draft 2020-12 relationship schema: PASS
- Relationship type/rule alignment: 20/20
- Valid fixture execution: 30/30
- Invalid expectation execution: 67/67
- Validator self-test: PASS
- Production-safety policy: PASS
- Determinism and protected-input immutability: PASS

Evidence requirements and structured conditions are controlled per predicate. High-risk compatibility assertions require authoritative evidence and explicit conditions. Only approved, error-free records with a production validation PASS may be considered for import. Synthetic fixtures and candidate records are never production-importable.

## Limitations And Deferred Work

No production relationship instances are included. `RELATED_TO` staging edges are excluded, virtual inverses are not materialized, condition-overlap detection is conservative, and human semantic approval remains required. Future-domain, Qdrant, and retrieval modeling are outside this release.

## Next Phase

Generate evidence-backed candidate relationships for human review. Preserve predicate semantics and backward compatibility; introduce additions in a minor version, and deprecate rather than silently redefine or remove published predicates.
