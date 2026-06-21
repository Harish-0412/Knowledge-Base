# Layer 3 Compatibility Loader - Implementation Plan

**Project:** CompatIQ - Neo4j-based Compatibility Intelligence Knowledge Graph  
**Layer:** Layer 3 - Compatibility Layer  
**Task:** Load compatibility rules into Neo4j  
**Date:** 2026-06-21

---

## 1. Executive Summary

This implementation plan describes the production-quality Layer 3 Compatibility Loader that loads existing compatibility rule artifacts into Neo4j while preserving all compatibility semantics, version constraints, evidence, and traceability. The loader integrates cleanly with the already-loaded Layer 1 (Domain Knowledge) and Layer 2 (Device Inventory) graphs.

**Key Constraints:**
- DO NOT redesign the architecture
- DO NOT simplify the model
- DO NOT regenerate rules
- DO NOT perform NLP extraction
- DO NOT create new ontology concepts
- DO NOT modify Layer 1 or Layer 2
- ONLY implement Layer 3 loading using existing compatibility rule artifacts

---

## 2. Current Project Status

### Layer 1 — Domain Knowledge Layer (Already Loaded)
- **69 Entity nodes** with labels: Entity, OperatingSystem, Firmware, Driver, SecurityComponent, ManagementTool, HardwarePlatform, DeviceModel, DeviceType
- **Status:** Complete and must NOT be modified

### Layer 2 — Device Inventory Layer (Already Loaded)
- **20 Device nodes**
- **262 ComponentInstance nodes**
- **262 HAS_COMPONENT relationships**
- **222 INSTANCE_OF relationships**
- **Status:** Complete and must NOT be modified

### Layer 3 — Compatibility Layer (To Be Loaded)
- **11 compatibility rules** in compatibility_rule_candidates.json
- **Status:** Rules exist as JSON, NOT yet loaded into Neo4j

---

## 3. Data Source Analysis

### Primary Source File
**Location:** `CompatibilityLayer/rules/candidate/compatibility_rule_candidates.json`

**Structure:**
- 11 rules total
- Each rule contains:
  - rule_id (e.g., "CRULE-FBAB6E52A6005CC3-001")
  - rule_type (min_version_constraint, known_issue_fixed, readiness_requirement, incompatible_combination)
  - predicate (REQUIRES, FIXED_BY, CONFLICTS_WITH)
  - subject (with entity_id, component_name, version_constraint)
  - object (with entity_id, component_name, version_constraint)
  - conditions array (version-specific applicability gates)
  - requirements array (version constraints)
  - exceptions array
  - remediations array
  - evidence array
  - severity, confidence, approval_status, verification_status
  - source_document_id, source_chunk_ids
  - timestamps

### Rule Types Present
1. **min_version_constraint** (6 rules)
2. **known_issue_fixed** (1 rule)
3. **readiness_requirement** (3 rules)
4. **incompatible_combination** (1 rule)

### Predicates Present
1. **REQUIRES** (8 rules)
2. **FIXED_BY** (1 rule)
3. **CONFLICTS_WITH** (2 rules)

---

## 4. Target Graph Model

### Node Types to Create

#### 4.1 CompatibilityRule
**Label:** `:CompatibilityRule`

**MERGE Key:** `rule_id`

**Properties:**
- rule_id (string, primary key)
- rule_type (string)
- predicate (string)
- severity (string)
- confidence (float)
- approval_status (string)
- verification_status (string)
- source_document_id (string)
- source_release (string)
- compatibility_ontology_version (string)
- created_timestamp (string, ISO 8601)
- updated_timestamp (string, ISO 8601)
- status (string)
- condition_logic (string)
- outcome (string)
- assertion_scope (string)

#### 4.2 VersionConstraint
**Label:** `:VersionConstraint`

**MERGE Key:** `entity_id + operator + version_normalized`

**Properties:**
- entity_id (string)
- entity_name (string)
- entity_kind (string)
- operator (string)
- version_raw (string)
- version_normalized (string)
- version_scheme (string)
- requirement_kind (string)

#### 4.3 Evidence
**Label:** `:Evidence`

**MERGE Key:** `evidence_id`

**Properties:**
- evidence_id (string)
- source_document_id (string)
- source_chunk_id (string)
- source_page (integer)
- source_excerpt (string)
- confidence_score (float)
- verification_status (string)
- extraction_method (string)
- source_type (string)

#### 4.4 Remediation (Optional)
**Label:** `:Remediation`

**MERGE Key:** `remediation_id`

**Properties:**
- remediation_id (string)
- remediation_type (string)
- target_entity_id (string)
- target_component_name (string)
- operator (string)
- target_version (string)
- sequence_order (integer)
- remediation_hint (string)

### Relationships to Create

#### 4.5 TARGETS
**From:** CompatibilityRule  
**To:** Entity (Layer 1)  
**Purpose:** Connect compatibility rules to Layer 1 domain entities

**Query Pattern:**
```cypher
MATCH (rule:CompatibilityRule {rule_id: $rule_id})
MATCH (entity:Entity {entity_id: $subject_entity_id})
MERGE (rule)-[:TARGETS]->(entity)
```

#### 4.6 HAS_CONSTRAINT
**From:** CompatibilityRule  
**To:** VersionConstraint  
**Purpose:** Connect rule to object version requirements

**Query Pattern:**
```cypher
MATCH (rule:CompatibilityRule {rule_id: $rule_id})
MERGE (rule)-[:HAS_CONSTRAINT]->(vc:VersionConstraint {
  entity_id: $object_entity_id,
  operator: $object_operator,
  version_normalized: $object_version_normalized
})
SET vc += $version_constraint_properties
```

#### 4.7 HAS_CONDITION
**From:** CompatibilityRule  
**To:** VersionConstraint  
**Purpose:** Create VersionConstraint nodes for rule conditions

**Query Pattern:**
```cypher
MATCH (rule:CompatibilityRule {rule_id: $rule_id})
MERGE (rule)-[:HAS_CONDITION]->(vc:VersionConstraint {
  entity_id: $condition_entity_id,
  operator: $condition_operator,
  version_normalized: $condition_version_normalized
})
SET vc += $condition_properties
```

#### 4.8 HAS_EVIDENCE
**From:** CompatibilityRule  
**To:** Evidence  
**Purpose:** Connect rules to supporting evidence

**Query Pattern:**
```cypher
MATCH (rule:CompatibilityRule {rule_id: $rule_id})
MERGE (rule)-[:HAS_EVIDENCE]->(ev:Evidence {evidence_id: $evidence_id})
SET ev += $evidence_properties
```

#### 4.9 HAS_REMEDIATION
**From:** CompatibilityRule  
**To:** Remediation  
**Purpose:** Connect rules to remediation actions

**Query Pattern:**
```cypher
MATCH (rule:CompatibilityRule {rule_id: $rule_id})
MERGE (rule)-[:HAS_REMEDIATION]->(rem:Remediation {remediation_id: $remediation_id})
SET rem += $remediation_properties
```

---

## 5. Loader Architecture

### 5.1 Design Principles
1. **MERGE Everywhere:** Use MERGE for all node and relationship creation to support safe reruns
2. **Batch Loading:** Process rules in batches to optimize performance
3. **Idempotency:** Multiple runs should produce the same result
4. **Error Handling:** Comprehensive error tracking and reporting
5. **Logging:** Detailed logging for debugging and audit trails
6. **Layer Integration:** Respect existing Layer 1 and Layer 2 structures

### 5.2 Processing Flow
```
1. Load compatibility_rule_candidates.json
2. Validate JSON structure
3. Connect to Neo4j using Neo4jConnection helper
4. For each rule:
   a. Create/update CompatibilityRule node
   b. Create/update VersionConstraint nodes for subject
   c. Create/update VersionConstraint nodes for object
   d. Create/update VersionConstraint nodes for conditions
   d. Create/update Evidence nodes
   e. Create/update Remediation nodes
   f. Create TARGETS relationship to Layer 1 Entity
   g. Create HAS_CONSTRAINT relationships
   h. Create HAS_CONDITION relationships
   i. Create HAS_EVIDENCE relationships
   j. Create HAS_REMEDIATION relationships
5. Generate load report
6. Close connection
```

### 5.3 Batch Strategy
- **Rule batch size:** 50 rules at a time
- **VersionConstraint batch size:** 100 constraints at a time
- **Evidence batch size:** 100 evidence records at a time
- **Remediation batch size:** 50 remediations at a time

---

## 6. Implementation Details

### 6.1 File Structure
```
scripts/loaders/
├── neo4j_connection.py (existing)
└── layer3_compatibility_loader.py (to be created)

reports/
└── layer3_load_report.json (to be generated)
```

### 6.2 Key Functions

#### load_compatibility_rules()
Main function that orchestrates the loading process.

#### create_compatibility_rule_node()
Creates or updates a CompatibilityRule node using MERGE.

#### create_version_constraint_node()
Creates or updates a VersionConstraint node using MERGE.

#### create_evidence_node()
Creates or updates an Evidence node using MERGE.

#### create_remediation_node()
Creates or updates a Remediation node using MERGE.

#### create_relationships()
Creates all required relationships using MERGE.

#### generate_load_report()
Generates the JSON load report with statistics.

### 6.3 Error Handling
- Validate JSON structure before processing
- Check for required fields in each rule
- Verify Layer 1 Entity references exist
- Log all errors with context
- Continue processing on non-fatal errors
- Aggregate errors in load report

### 6.4 Logging Strategy
- INFO: Normal operations, progress updates
- WARNING: Non-critical issues, missing optional fields
- ERROR: Critical issues that prevent loading
- DEBUG: Detailed processing information

---

## 7. Expected Counts After Successful Import

Based on the 11 rules in compatibility_rule_candidates.json:

### Node Counts
- **CompatibilityRule:** 11 nodes
- **VersionConstraint:** Approximately 33-44 nodes (subject + object + conditions per rule)
- **Evidence:** 11 nodes (one per rule)
- **Remediation:** 11 nodes (one per rule)

### Relationship Counts
- **TARGETS:** 11 relationships (one per rule to Layer 1 Entity)
- **HAS_CONSTRAINT:** 11 relationships (one per rule to object constraint)
- **HAS_CONDITION:** Approximately 11-22 relationships (conditions vary per rule)
- **HAS_EVIDENCE:** 11 relationships (one per rule)
- **HAS_REMEDIATION:** 11 relationships (one per rule)

**Total Relationships:** Approximately 55-66 relationships

---

## 8. Validation Strategy

### 8.1 Pre-Load Validation
- Verify compatibility_rule_candidates.json exists and is valid JSON
- Check Neo4j connection is available
- Verify Layer 1 Entity nodes exist for all referenced entity_ids

### 8.2 Post-Load Validation
- Count CompatibilityRule nodes (should equal 11)
- Count VersionConstraint nodes (should be approximately 33-44)
- Count Evidence nodes (should equal 11)
- Count TARGETS relationships (should equal 11)
- Count HAS_CONSTRAINT relationships (should equal 11)
- Count HAS_CONDITION relationships (should match conditions count)
- Count HAS_EVIDENCE relationships (should equal 11)
- Count HAS_REMEDIATION relationships (should equal 11)
- Verify no CompatibilityRule nodes without TARGETS relationships
- Verify no orphaned VersionConstraint nodes

### 8.3 Data Integrity Checks
- Verify all rule_ids are unique
- Verify all evidence_ids are unique
- Verify all remediation_ids are unique
- Verify all Layer 1 Entity references exist
- Verify all timestamps are valid ISO 8601 format

---

## 9. Assumptions and Mapping Decisions

### 9.1 Assumptions
1. Layer 1 Entity nodes are already loaded and accessible
2. Neo4j connection credentials are available via environment variables
3. compatibility_rule_candidates.json is the single source of truth
4. All rules in the file should be loaded (no filtering)
5. Version constraint MERGE key is entity_id + operator + version_normalized
6. Evidence MERGE key is evidence_id
7. Remediation MERGE key is remediation_id

### 9.2 Mapping Decisions
1. **Subject → TARGETS → Entity:** Map rule.subject.entity_id to Layer 1 Entity
2. **Object → HAS_CONSTRAINT → VersionConstraint:** Create constraint node for object
3. **Conditions → HAS_CONDITION → VersionConstraint:** Create constraint nodes for each condition
4. **Evidence → HAS_EVIDENCE → Evidence:** Create evidence node per evidence record
5. **Remediations → HAS_REMEDIATION → Remediation:** Create remediation node per remediation
6. **Predicate stored as property:** Store predicate on CompatibilityRule node (not as relationship type)
7. **Version constraints normalized:** Use version_normalized for MERGE keys, preserve version_raw as property

### 9.3 Design Decisions
1. **Central CompatibilityRule node:** CompatibilityRule remains the central node, not direct Entity-to-Entity relationships
2. **Version-specific constraints:** All version information preserved in VersionConstraint nodes
3. **Evidence traceability:** Full evidence chain preserved via HAS_EVIDENCE relationships
4. **Remediation linkage:** Remediation actions linked via HAS_REMEDIATION relationships
5. **MERGE for idempotency:** All operations use MERGE to support safe reruns

---

## 10. Deliverables

1. **Implementation Plan:** This document
2. **Final Graph Schema:** Detailed schema documentation
3. **Neo4j Model Explanation:** Architecture and design rationale
4. **Loader Architecture:** Detailed loader design
5. **Python Implementation:** layer3_compatibility_loader.py
6. **Cypher Strategy:** Query patterns and optimization
7. **Validation Queries:** Cypher queries for validation
8. **Expected Counts:** Post-import node and relationship counts
9. **Assumptions Document:** Mapping decisions and assumptions

---

## 11. Next Steps

1. Create final graph schema documentation
2. Implement layer3_compatibility_loader.py
3. Create validation Cypher queries
4. Generate comprehensive documentation
5. Test loader with sample data
6. Validate import results
