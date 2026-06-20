# Compatibility Rule Generation Guide

Phase 7 generates unapproved candidate rules only from Phase 6 records marked `eligible_for_rule_generation`. Run:

```powershell
python scripts/generate_compatibility_rules.py --corrected-input CompatibilityLayer/rules/corrected/corrected_rule_candidates.json --compatibility-ontology CompatibilityLayer/ontology --domain-registry ontology/releases/v1.1-rc2/canonical_entity_registry.json --output-dir CompatibilityLayer/rules/candidate --clarification-dir CompatibilityLayer/rules/needs_clarification
```

Every rule has deterministic lineage, `approval_status: candidate`, and `verification_status: review_required`. Production import is disabled. Unrepresentable or unresolved semantics are written to `CompatibilityLayer/rules/needs_clarification/compatibility_rules_needing_clarification.json` for Phase 9. Phase 8 should consume the candidate rules, manifest, and generation trace listed in the readiness report.
