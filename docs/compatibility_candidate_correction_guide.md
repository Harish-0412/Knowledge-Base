# Compatibility Candidate Correction Guide

Phase 6 normalizes the 42 raw candidates without approving or overwriting them. Run:

```powershell
python scripts/correct_compatibility_candidates.py --input CompatibilityLayer/source/raw/normalized_rule_candidates.json --analysis-dir CompatibilityLayer/analysis --resolution-dir CompatibilityLayer/resolution --output-dir CompatibilityLayer/rules/corrected
```

The output includes corrected candidates, field-level correction traces, split lineage, accounting, and a human clarification queue. `RCAND-000365` is split into two lineage-linked support candidates. Ambiguous, unresolved, optional, advisory, or contradictory candidates remain in clarification and are not eligible for generation.

The raw source is protected by its SHA-256 checksum. `--dry-run` parses and checks the source without writing files.
