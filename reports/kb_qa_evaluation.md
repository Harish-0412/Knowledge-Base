# Knowledge Base QA Evaluation Report

**Report generated on**: 2026-06-19T21:34:56.281170

## Overall Score

- Total test cases: 54
- Answered: 50
- Partially Answered: 0
- Ambiguous: 0
- Not Found: 1
- Unsupported: 3

- Entity Identification Accuracy: 88.89%
- Expected Status Accuracy: 100.00%

## Readiness Assessment

### Entity-Knowledge Readiness
- Status: **Partial**
- Entity definition, purpose, and classification questions are well-supported.
- More than 50% of entity lookup tests pass.

### Cross-Reference Readiness
- Status: **Partial**
- Basic cross-domain lookups work, but explicit semantic relationships are not stored.

### Semantic-Relationship Readiness
- Status: **Not Ready**
- No explicit semantic relationships (requires/supports/enables) are modeled yet.

### Compatibility-Question Readiness
- Status: **Not Ready**
- Explicit compatibility relationships are not stored in the knowledge base.
- All compatibility questions are correctly marked as 'unsupported_by_current_kb'.

## Per-Category Results

- **entity_definition**: 24/27 (88.89%)
- **purpose**: 2/2 (100.00%)
- **classification**: 3/3 (100.00%)
- **type_subtype**: 4/4 (100.00%)
- **alias_lookup**: 5/5 (100.00%)
- **keyword_lookup**: 0/3 (0.00%)
- **related_entities**: 3/3 (100.00%)
- **cross_domain**: 0/1 (0.00%)
- **negative_lookup**: 3/3 (100.00%)
- **unsupported_compatibility**: 3/3 (100.00%)

## Per-Domain Results

- **Firmware**: 12/12 (100.00%)
- **Security**: 10/10 (100.00%)
- **Operating_system**: 9/9 (100.00%)
- **Drivers**: 4/4 (100.00%)
- **Management**: 6/6 (100.00%)

## Missing Required Terms

- Test test-007: Measured Boot
- Test test-009: Security
- Test test-029: Secure Boot
- Test test-030: TPM
- Test test-036: Security Enhanced Linux
- Test test-044: Canonical
- Test test-045: Red Hat Enterprise Linux

## Failed Tests


### Test test-007
- Question: Which entities relate to measured boot?
- Failure: Missing required terms: Measured Boot
- Expected Status: answered
- Actual Status: answered

### Test test-009
- Question: Which security concepts are referenced by firmware entities?
- Failure: Missing required terms: Security
- Expected Status: answered
- Actual Status: answered

### Test test-029
- Question: Which entities relate to Secure Boot?
- Failure: Missing required terms: Secure Boot
- Expected Status: answered
- Actual Status: answered

### Test test-030
- Question: Which entities relate to TPM?
- Failure: Missing required terms: TPM
- Expected Status: answered
- Actual Status: answered

### Test test-036
- Question: What is SELinux?
- Failure: Missing required terms: Security Enhanced Linux
- Expected Status: answered
- Actual Status: answered

### Test test-044
- Question: What is Ubuntu?
- Failure: Missing required terms: Canonical
- Expected Status: answered
- Actual Status: answered

### Test test-045
- Question: What is RHEL?
- Failure: Missing required terms: Red Hat Enterprise Linux
- Expected Status: answered
- Actual Status: answered

## Recommended Ontology Improvements

1. Add explicit semantic relationship triples (entity, relationship, entity)
2. Add compatibility matrix entries
3. Expand entity coverage for hardware concepts
4. Add more keyword synonyms to improve keyword search
5. Consider adding a fuzzy matching threshold for ambiguous queries
