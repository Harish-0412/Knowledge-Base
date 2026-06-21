# Layer 3 Compatibility Layer - Final Graph Schema

**Project:** CompatIQ - Neo4j-based Compatibility Intelligence Knowledge Graph  
**Layer:** Layer 3 - Compatibility Layer  
**Schema Version:** 1.0.0  
**Date:** 2026-06-21

---

## 1. Schema Overview

This document defines the final graph schema for Layer 3 (Compatibility Layer) of the CompatIQ knowledge graph. The schema is designed to load existing compatibility rule artifacts into Neo4j while preserving all compatibility semantics, version constraints, evidence, and traceability.

### Design Principles
1. **CompatibilityRule as Central Node:** All compatibility information centers on the CompatibilityRule node
2. **Version-Specific Constraints:** Version information preserved in dedicated VersionConstraint nodes
3. **Layer Integration:** TARGETS relationship connects to Layer 1 Entity nodes
4. **Evidence Traceability:** Full evidence chain preserved via HAS_EVIDENCE relationships
5. **Idempotent Loading:** MERGE operations support safe reruns

---

## 2. Node Types

### 2.1 CompatibilityRule

**Label:** `:CompatibilityRule`

**Purpose:** Represents a machine-readable compatibility assertion between components.

**MERGE Key:** `rule_id`

**Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| rule_id | string | YES | Unique identifier (e.g., "CRULE-FBAB6E52A6005CC3-001") |
| rule_type | string | YES | Type of rule (min_version_constraint, known_issue_fixed, readiness_requirement, incompatible_combination) |
| predicate | string | YES | Relationship type (REQUIRES, FIXED_BY, CONFLICTS_WITH) |
| severity | string | YES | Severity level (critical, warning, info) |
| confidence | float | YES | Confidence score (0.0 to 1.0) |
| approval_status | string | YES | Approval status (candidate, approved, rejected, superseded) |
| verification_status | string | YES | Verification status (review_required, verified) |
| source_document_id | string | YES | Source document identifier |
| source_release | string | YES | Source release version |
| compatibility_ontology_version | string | YES | Ontology version used |
| created_timestamp | string | YES | ISO 8601 timestamp |
| updated_timestamp | string | YES | ISO 8601 timestamp |
| status | string | YES | Current status |
| condition_logic | string | YES | Logic for combining conditions (AND, OR) |
| outcome | string | YES | Rule outcome type |
| assertion_scope | string | YES | Scope of assertion |

**Example:**
```cypher
(:CompatibilityRule {
  rule_id: "CRULE-AEADF7F483FE03B6-001",
  rule_type: "min_version_constraint",
  predicate: "REQUIRES",
  severity: "critical",
  confidence: 1.0,
  approval_status: "candidate",
  verification_status: "review_required",
  source_document_id: "DOC-CA114A84AE60",
  source_release: "1.1.0-rc2",
  compatibility_ontology_version: "1.0.0",
  created_timestamp: "2026-06-20T00:00:00+00:00",
  updated_timestamp: "2026-06-20T00:00:00+00:00",
  status: "candidate",
  condition_logic: "AND",
  outcome: "conditional",
  assertion_scope: "version_specific"
})
```

---

### 2.2 VersionConstraint

**Label:** `:VersionConstraint`

**Purpose:** Represents a version-based requirement or condition for a component.

**MERGE Key:** `entity_id + operator + version_normalized`

**Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| entity_id | string | YES | Entity identifier from Layer 1 registry (e.g., "FW-013") |
| entity_name | string | YES | Entity name (e.g., "System Firmware") |
| entity_kind | string | YES | Entity kind (Firmware, Driver, Operating System, Security, Management) |
| operator | string | YES | Comparison operator (==, !=, >=, <=, >, <) |
| version_raw | string | YES | Original version string from source |
| version_normalized | string | YES | Normalized version string for comparison |
| version_scheme | string | YES | Version scheme (semantic, wildcard, named_release, calendar) |
| requirement_kind | string | YES | Requirement type (min_version, max_version, exact_version, version_range) |

**Example:**
```cypher
(:VersionConstraint {
  entity_id: "FW-013",
  entity_name: "System Firmware",
  entity_kind: "Firmware",
  operator: ">=",
  version_raw: "8.2.0",
  version_normalized: "8.2.0",
  version_scheme: "semantic",
  requirement_kind: "min_version"
})
```

---

### 2.3 Evidence

**Label:** `:Evidence`

**Purpose:** Represents traceable reference to authoritative source that substantiates a rule.

**MERGE Key:** `evidence_id`

**Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| evidence_id | string | YES | Unique evidence identifier |
| source_document_id | string | YES | Source document identifier |
| source_chunk_id | string | YES | Chunk identifier within document |
| source_page | integer | YES | Page number in source document |
| source_excerpt | string | YES | Text excerpt from source |
| confidence_score | float | YES | Confidence score (0.0 to 1.0) |
| verification_status | string | YES | Verification status |
| extraction_method | string | YES | Method used to extract evidence |
| source_type | string | YES | Type of source document |

**Example:**
```cypher
(:Evidence {
  evidence_id: "EVID-RCAND000363-001",
  source_document_id: "DOC-CA114A84AE60",
  source_chunk_id: "CHUNK-000385",
  source_page: 1,
  source_excerpt: "System BIOS 6.4.2 requires System Firmware 8.2.0 or later.",
  confidence_score: 1.0,
  verification_status: "review_required",
  extraction_method: "nlp_extraction",
  source_type: "ingested_document"
})
```

---

### 2.4 Remediation

**Label:** `:Remediation`

**Purpose:** Represents prescribed corrective action to resolve a compatibility violation.

**MERGE Key:** `remediation_id`

**Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| remediation_id | string | YES | Unique remediation identifier |
| remediation_type | string | YES | Type of remediation (version_upgrade, version_downgrade, configuration_change) |
| target_entity_id | string | YES | Target entity identifier |
| target_component_name | string | YES | Target component name |
| operator | string | YES | Version comparison operator |
| target_version | string | YES | Target version for remediation |
| sequence_order | integer | YES | Order in remediation sequence |
| remediation_hint | string | YES | Human-readable remediation instruction |

**Example:**
```cypher
(:Remediation {
  remediation_id: "REM-RCAND000363-001",
  remediation_type: "version_upgrade",
  target_entity_id: "FW-013",
  target_component_name: "System Firmware",
  operator: ">=",
  target_version: "8.2.0",
  sequence_order: 1,
  remediation_hint: "Ensure System Firmware is updated to version 8.2.0 or later before installing System BIOS 6.4.2."
})
```

---

## 3. Relationship Types

### 3.1 TARGETS

**From:** `:CompatibilityRule`  
**To:** `:Entity` (Layer 1)  
**Purpose:** Connects compatibility rule to the subject Layer 1 entity

**Properties:** None

**Example:**
```cypher
(:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[:TARGETS]->(:Entity {entity_id: "FW-001"})
```

**Semantic Meaning:** This rule applies to the BIOS entity in the Domain Knowledge Layer.

---

### 3.2 HAS_CONSTRAINT

**From:** `:CompatibilityRule`  
**To:** `:VersionConstraint`  
**Purpose:** Connects rule to object version requirements

**Properties:** None

**Example:**
```cypher
(:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[:HAS_CONSTRAINT]->(:VersionConstraint {
  entity_id: "FW-013",
  operator: ">=",
  version_normalized: "8.2.0"
})
```

**Semantic Meaning:** This rule requires System Firmware to be at version 8.2.0 or later.

---

### 3.3 HAS_CONDITION

**From:** `:CompatibilityRule`  
**To:** `:VersionConstraint`  
**Purpose:** Connects rule to applicability conditions

**Properties:** None

**Example:**
```cypher
(:CompatibilityRule {rule_id: "CRULE-FBAB6E52A6005CC3-001"})-[:HAS_CONDITION]->(:VersionConstraint {
  entity_id: "OS-013",
  operator: "==",
  version_normalized: "2026.1"
})
```

**Semantic Meaning:** This rule applies only when Enterprise OS 2026.1 is installed.

---

### 3.4 HAS_EVIDENCE

**From:** `:CompatibilityRule`  
**To:** `:Evidence`  
**Purpose:** Connects rule to supporting evidence

**Properties:** None

**Example:**
```cypher
(:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[:HAS_EVIDENCE]->(:Evidence {
  evidence_id: "EVID-RCAND000363-001"
})
```

**Semantic Meaning:** This rule is substantiated by the specified evidence record.

---

### 3.5 HAS_REMEDIATION

**From:** `:CompatibilityRule`  
**To:** `:Remediation`  
**Purpose:** Connects rule to remediation actions

**Properties:** None

**Example:**
```cypher
(:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[:HAS_REMEDIATION]->(:Remediation {
  remediation_id: "REM-RCAND000363-001"
})
```

**Semantic Meaning:** This rule prescribes the specified remediation action.

---

## 4. Graph Structure Examples

### 4.1 Simple REQUIRES Rule

```
BIOS 6.4.2 REQUIRES System Firmware >= 8.2.0

(:CompatibilityRule {
  rule_id: "CRULE-AEADF7F483FE03B6-001",
  predicate: "REQUIRES",
  rule_type: "min_version_constraint"
})
  |
  | TARGETS
  v
(:Entity {entity_id: "FW-001", name: "BIOS"})
  ^
  |
  | HAS_CONSTRAINT
  |
(:VersionConstraint {
  entity_id: "FW-013",
  entity_name: "System Firmware",
  operator: ">=",
  version_normalized: "8.2.0"
})
  ^
  |
  | HAS_CONDITION
  |
(:VersionConstraint {
  entity_id: "FW-001",
  entity_name: "BIOS",
  operator: "==",
  version_normalized: "6.4.2"
})
```

### 4.2 Rule with Evidence and Remediation

```
Enterprise OS 2026.1 REQUIRES Driver Pack >= 12.4.0

(:CompatibilityRule {
  rule_id: "CRULE-FBAB6E52A6005CC3-001",
  predicate: "REQUIRES"
})
  |
  +--[:TARGETS]--> (:Entity {entity_id: "OS-013", name: "Enterprise OS"})
  |
  +--[:HAS_CONSTRAINT]--> (:VersionConstraint {
    entity_id: "DRV-009",
    operator: ">=",
    version_normalized: "12.4.0"
  })
  |
  +--[:HAS_CONDITION]--> (:VersionConstraint {
    entity_id: "OS-013",
    operator: "==",
    version_normalized: "2026.1"
  })
  |
  +--[:HAS_EVIDENCE]--> (:Evidence {
    evidence_id: "EVID-RCAND000360-001"
  })
  |
  +--[:HAS_REMEDIATION]--> (:Remediation {
    remediation_id: "REM-RCAND000360-001"
  })
```

### 4.3 CONFLICTS_WITH Rule

```
Security Agent 4.8.3 CONFLICTS_WITH Endpoint Agent < 3.7.0

(:CompatibilityRule {
  rule_id: "CRULE-26AF9B5E643E194B-001",
  predicate: "CONFLICTS_WITH",
  rule_type: "incompatible_combination"
})
  |
  | TARGETS
  v
(:Entity {entity_id: "SEC-004", name: "EDR Agent"})
  ^
  |
  | HAS_CONSTRAINT
  |
(:VersionConstraint {
  entity_id: "MGT-010",
  entity_name: "Endpoint Agent",
  operator: ">=",
  version_normalized: "3.7.0"
})
```

---

## 5. Schema Constraints and Indexes

### 5.1 Uniqueness Constraints

```cypher
// CompatibilityRule uniqueness
CREATE CONSTRAINT compatibility_rule_rule_id_unique IF NOT EXISTS FOR (r:CompatibilityRule) REQUIRE r.rule_id IS UNIQUE;

// Evidence uniqueness
CREATE CONSTRAINT evidence_evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE;

// Remediation uniqueness
CREATE CONSTRAINT remediation_remediation_id_unique IF NOT EXISTS FOR (r:Remediation) REQUIRE r.remediation_id IS UNIQUE;
```

### 5.2 Indexes

```cypher
// VersionConstraint composite index for MERGE operations
CREATE INDEX version_constraint_composite IF NOT EXISTS FOR (vc:VersionConstraint) ON (vc.entity_id, vc.operator, vc.version_normalized);

// Entity index for TARGETS lookups
CREATE INDEX entity_entity_id IF NOT EXISTS FOR (e:Entity) ON (e.entity_id);

// CompatibilityRule indexes for common queries
CREATE INDEX compatibility_rule_rule_type IF NOT EXISTS FOR (r:CompatibilityRule) ON (r.rule_type);
CREATE INDEX compatibility_rule_predicate IF NOT EXISTS FOR (r:CompatibilityRule) ON (r.predicate);
CREATE INDEX compatibility_rule_severity IF NOT EXISTS FOR (r:CompatibilityRule) ON (r.severity);
CREATE INDEX compatibility_rule_approval_status IF NOT EXISTS FOR (r:CompatibilityRule) ON (r.approval_status);
```

---

## 6. Integration with Existing Layers

### 6.1 Layer 1 Integration

**Existing Layer 1 Structure:**
```
(:Entity:OperatingSystem {entity_id: "OS-013", name: "Enterprise OS"})
(:Entity:Firmware {entity_id: "FW-001", name: "BIOS"})
(:Entity:Firmware {entity_id: "FW-013", name: "System Firmware"})
(:Entity:Driver {entity_id: "DRV-009", name: "Driver Pack"})
(:Entity:Security {entity_id: "SEC-004", name: "EDR Agent"})
(:Entity:Management {entity_id: "MGT-010", name: "Endpoint Agent"})
```

**Layer 3 Integration via TARGETS:**
```
(:CompatibilityRule)-[:TARGETS]->(:Entity)
```

### 6.2 Layer 2 Integration

**Existing Layer 2 Structure:**
```
(:Device)-[:HAS_COMPONENT]->(:ComponentInstance)-[:INSTANCE_OF]->(:Entity)
```

**Layer 3 does not directly connect to Layer 2.** Compatibility rules evaluate against Layer 1 entities, which Layer 2 component instances reference via INSTANCE_OF relationships.

---

## 7. Expected Graph Statistics

Based on 11 rules in compatibility_rule_candidates.json:

### Node Counts
- **CompatibilityRule:** 11
- **VersionConstraint:** ~33-44 (subject + object + conditions per rule)
- **Evidence:** 11
- **Remediation:** 11

### Relationship Counts
- **TARGETS:** 11
- **HAS_CONSTRAINT:** 11
- **HAS_CONDITION:** ~11-22
- **HAS_EVIDENCE:** 11
- **HAS_REMEDIATION:** 11

**Total Relationships:** ~55-66

---

## 8. Schema Evolution Considerations

### 8.1 Future Extensions
The schema supports future additions without breaking existing data:
- Additional node types (e.g., Exception, ConflictConstraint)
- Additional relationship types (e.g., HAS_EXCEPTION, SUPERSEDES)
- Additional properties on existing nodes

### 8.2 Backward Compatibility
- MERGE operations ensure idempotent loading
- New optional properties can be added without affecting existing nodes
- New relationship types can be added without affecting existing relationships

---

## 9. Schema Validation Rules

### 9.1 Node Validation
- Every CompatibilityRule must have exactly one TARGETS relationship
- Every CompatibilityRule must have at least one HAS_CONSTRAINT relationship
- Every VersionConstraint must be connected to at least one CompatibilityRule
- Every Evidence must be connected to at least one CompatibilityRule
- Every Remediation must be connected to at least one CompatibilityRule

### 9.2 Relationship Validation
- TARGETS must point to existing Layer 1 Entity nodes
- HAS_CONSTRAINT must point to VersionConstraint nodes
- HAS_CONDITION must point to VersionConstraint nodes
- HAS_EVIDENCE must point to Evidence nodes
- HAS_REMEDIATION must point to Remediation nodes

### 9.3 Data Validation
- rule_id must be unique across all CompatibilityRule nodes
- evidence_id must be unique across all Evidence nodes
- remediation_id must be unique across all Remediation nodes
- VersionConstraint composite key (entity_id + operator + version_normalized) must be unique
- All timestamps must be valid ISO 8601 format
- All confidence scores must be between 0.0 and 1.0

---

## 10. Cypher Query Patterns

### 10.1 Create CompatibilityRule Node
```cypher
MERGE (r:CompatibilityRule {rule_id: $rule_id})
SET r += $properties
```

### 10.2 Create VersionConstraint Node
```cypher
MERGE (vc:VersionConstraint {
  entity_id: $entity_id,
  operator: $operator,
  version_normalized: $version_normalized
})
SET vc += $properties
```

### 10.3 Create Evidence Node
```cypher
MERGE (e:Evidence {evidence_id: $evidence_id})
SET e += $properties
```

### 10.4 Create Remediation Node
```cypher
MERGE (rem:Remediation {remediation_id: $remediation_id})
SET rem += $properties
```

### 10.5 Create TARGETS Relationship
```cypher
MATCH (r:CompatibilityRule {rule_id: $rule_id})
MATCH (e:Entity {entity_id: $entity_id})
MERGE (r)-[:TARGETS]->(e)
```

### 10.6 Create HAS_CONSTRAINT Relationship
```cypher
MATCH (r:CompatibilityRule {rule_id: $rule_id})
MATCH (vc:VersionConstraint {
  entity_id: $entity_id,
  operator: $operator,
  version_normalized: $version_normalized
})
MERGE (r)-[:HAS_CONSTRAINT]->(vc)
```

### 10.7 Create HAS_CONDITION Relationship
```cypher
MATCH (r:CompatibilityRule {rule_id: $rule_id})
MATCH (vc:VersionConstraint {
  entity_id: $entity_id,
  operator: $operator,
  version_normalized: $version_normalized
})
MERGE (r)-[:HAS_CONDITION]->(vc)
```

### 10.8 Create HAS_EVIDENCE Relationship
```cypher
MATCH (r:CompatibilityRule {rule_id: $rule_id})
MATCH (e:Evidence {evidence_id: $evidence_id})
MERGE (r)-[:HAS_EVIDENCE]->(e)
```

### 10.9 Create HAS_REMEDIATION Relationship
```cypher
MATCH (r:CompatibilityRule {rule_id: $rule_id})
MATCH (rem:Remediation {remediation_id: $remediation_id})
MERGE (r)-[:HAS_REMEDIATION]->(rem)
```

---

## 11. Schema Summary

This schema provides a complete, production-ready graph model for Layer 3 compatibility rules that:
- Preserves all compatibility semantics from source artifacts
- Maintains version-specific constraint information
- Ensures evidence traceability
- Supports remediation workflows
- Integrates cleanly with existing Layer 1 and Layer 2 graphs
- Supports idempotent loading via MERGE operations
- Enables efficient querying through appropriate indexes and constraints
