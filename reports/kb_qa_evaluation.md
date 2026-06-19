# Knowledge Base QA Evaluation Report

**Report generated on**: 2026-06-19T21:04:43.808018

## Overall Score

- Total test cases: 54
- Answered: 44
- Partially Answered: 0
- Ambiguous: 0
- Not Found: 7
- Unsupported: 3

- Entity Identification Accuracy: 88.89%
- Expected Status Accuracy: 88.89%

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

- **entity_definition**: 16/27 (59.26%)
- **purpose**: 1/2 (50.00%)
- **classification**: 3/3 (100.00%)
- **type_subtype**: 4/4 (100.00%)
- **alias_lookup**: 0/5 (0.00%)
- **keyword_lookup**: 3/3 (100.00%)
- **related_entities**: 3/3 (100.00%)
- **cross_domain**: 0/1 (0.00%)
- **negative_lookup**: 2/3 (66.67%)
- **unsupported_compatibility**: 3/3 (100.00%)

## Per-Domain Results

- **Firmware**: 8/8 (100.00%)
- **Security**: 9/9 (100.00%)
- **Operating_system**: 9/9 (100.00%)
- **Drivers**: 2/2 (100.00%)
- **Management**: 2/2 (100.00%)

## Missing Required Terms

- Test test-003: purpose
- Test test-006: BIOS
- Test test-009: TPM, Secure Boot
- Test test-016: encryption
- Test test-017: encryption
- Test test-019: UEFI
- Test test-020: Active Directory
- Test test-021: Group Policy
- Test test-022: Windows Server Update Services
- Test test-036: Security Enhanced Linux
- Test test-038: encryption
- Test test-039: Windows Display Driver Model
- Test test-040: Network Driver Interface Specification
- Test test-041: Advanced Configuration and Power Interface
- Test test-042: GUID Partition Table
- Test test-044: Canonical
- Test test-045: Red Hat Enterprise Linux
- Test test-046: Security Information and Event Management
- Test test-054: does not exist

## Failed Tests


### Test test-003
- Question: What is the purpose of UEFI?
- Failure: Missing required terms: purpose
- Expected Status: answered
- Actual Status: answered

### Test test-006
- Question: What does Basic Input/Output System refer to?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: BIOS
- Expected Status: answered
- Actual Status: not_found

### Test test-009
- Question: Which security concepts are referenced by firmware entities?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: TPM, Secure Boot
- Expected Status: answered
- Actual Status: not_found

### Test test-016
- Question: What is BitLocker?
- Failure: Missing required terms: encryption
- Expected Status: answered
- Actual Status: answered

### Test test-017
- Question: What is FileVault?
- Failure: Missing required terms: encryption
- Expected Status: answered
- Actual Status: answered

### Test test-019
- Question: What does EFI refer to?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: UEFI
- Expected Status: answered
- Actual Status: not_found

### Test test-020
- Question: What does AD refer to?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: Active Directory
- Expected Status: answered
- Actual Status: not_found

### Test test-021
- Question: What does GPO refer to?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: Group Policy
- Expected Status: answered
- Actual Status: not_found

### Test test-022
- Question: What does WSUS refer to?
- Failure: Status mismatch: expected 'answered', got 'not_found'
- Failure: Missing required terms: Windows Server Update Services
- Expected Status: answered
- Actual Status: not_found

### Test test-036
- Question: What is SELinux?
- Failure: Missing required terms: Security Enhanced Linux
- Expected Status: answered
- Actual Status: answered

### Test test-038
- Question: What is LUKS?
- Failure: Missing required terms: encryption
- Expected Status: answered
- Actual Status: answered

### Test test-039
- Question: What is WDDM?
- Failure: Missing required terms: Windows Display Driver Model
- Expected Status: answered
- Actual Status: answered

### Test test-040
- Question: What is NDIS?
- Failure: Missing required terms: Network Driver Interface Specification
- Expected Status: answered
- Actual Status: answered

### Test test-041
- Question: What is ACPI?
- Failure: Missing required terms: Advanced Configuration and Power Interface
- Expected Status: answered
- Actual Status: answered

### Test test-042
- Question: What is GPT?
- Failure: Missing required terms: GUID Partition Table
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

### Test test-046
- Question: What is SIEM?
- Failure: Missing required terms: Security Information and Event Management
- Expected Status: answered
- Actual Status: answered

### Test test-054
- Question: What is FakeEntityThatDoesNotExist?
- Failure: Missing required terms: does not exist
- Expected Status: not_found
- Actual Status: not_found

## Recommended Ontology Improvements

1. Add explicit semantic relationship triples (entity, relationship, entity)
2. Add compatibility matrix entries
3. Expand entity coverage for hardware concepts
4. Add more keyword synonyms to improve keyword search
5. Consider adding a fuzzy matching threshold for ambiguous queries
