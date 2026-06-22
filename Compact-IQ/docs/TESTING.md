# TESTING — CompatIQ

## 1. Schema Tests

- Validate sample documents against `document.schema.json`.
- Validate chunks against `document_chunk.schema.json`.
- Validate rule candidates and approved rules.
- Validate inventory snapshot and device records.
- Validate compliance results and violations.

## 2. Normalization Tests

Test these conversions:

```text
02.00.21 → 2.0.21
v2.0.21 → 2.0.21
Intel(R) Xeon(R) CPU E5-2400 v2 → intel_xeon_e5_2400_v2
System BIOS → bios
or later → >=
```

## 3. Compliance Engine Tests

### Test 1: Direct pass
Device satisfies all requirements.

### Test 2: Direct fail
Device BIOS below required version.

### Test 3: Compound condition pass/fail
Rule applies only when all AND conditions match.

### Test 4: Rule not applicable
Device does not match condition set, so no violation.

### Test 5: Missing data
Device should return unknown or needs review.

### Test 6: Readiness failure
Device compatible but not rollout-ready.

## 4. Graph Tests

- Approved rule creates Rule, ConditionSet, Condition, Requirement nodes.
- Device creates Device and ComponentInstance nodes.
- Violation creates Device→VIOLATES→Rule relationship.
- Explanation graph returns source chunk and remediation step.

## 5. API Tests

- Upload document
- Extract chunks
- Extract rules
- Review candidate
- Upload inventory
- Run scan
- Get device explanation
- Get graph export

## 6. Demo Acceptance Test

A fresh run should complete:

```text
load fixtures
run scan
show dashboard
open critical device
show graph
show remediation
export report
```
