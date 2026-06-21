# Layer 3 Compatibility Layer - Validation Cypher Queries

**Project:** CompatIQ - Neo4j-based Compatibility Intelligence Knowledge Graph  
**Layer:** Layer 3 - Compatibility Layer  
**Date:** 2026-06-21

---

## 1. Node Count Queries

### 1.1 Count CompatibilityRule Nodes
```cypher
MATCH (n:CompatibilityRule)
RETURN count(n) AS compatibility_rule_count;
```

**Expected Result:** 11 (based on compatibility_rule_candidates.json)

---

### 1.2 Count VersionConstraint Nodes
```cypher
MATCH (n:VersionConstraint)
RETURN count(n) AS version_constraint_count;
```

**Expected Result:** Approximately 33-44 (subject + object + conditions per rule)

---

### 1.3 Count Evidence Nodes
```cypher
MATCH (n:Evidence)
RETURN count(n) AS evidence_count;
```

**Expected Result:** 11 (one per rule)

---

### 1.4 Count Remediation Nodes
```cypher
MATCH (n:Remediation)
RETURN count(n) AS remediation_count;
```

**Expected Result:** 11 (one per rule)

---

## 2. Relationship Count Queries

### 2.1 Count TARGETS Relationships
```cypher
MATCH ()-[r:TARGETS]->()
RETURN count(r) AS targets_count;
```

**Expected Result:** 11 (one per rule)

---

### 2.2 Count HAS_CONSTRAINT Relationships
```cypher
MATCH ()-[r:HAS_CONSTRAINT]->()
RETURN count(r) AS has_constraint_count;
```

**Expected Result:** 11 (one per rule to object constraint)

---

### 2.3 Count HAS_CONDITION Relationships
```cypher
MATCH ()-[r:HAS_CONDITION]->()
RETURN count(r) AS has_condition_count;
```

**Expected Result:** Approximately 11-22 (conditions vary per rule)

---

### 2.4 Count HAS_EVIDENCE Relationships
```cypher
MATCH ()-[r:HAS_EVIDENCE]->()
RETURN count(r) AS has_evidence_count;
```

**Expected Result:** 11 (one per rule)

---

### 2.5 Count HAS_REMEDIATION Relationships
```cypher
MATCH ()-[r:HAS_REMEDIATION]->()
RETURN count(r) AS has_remediation_count;
```

**Expected Result:** 11 (one per rule)

---

## 3. Data Integrity Queries

### 3.1 Verify All CompatibilityRule Nodes Have TARGETS Relationships
```cypher
MATCH (r:CompatibilityRule)
WHERE NOT (r)-[:TARGETS]->(:Entity)
RETURN r.rule_id, r.rule_type;
```

**Expected Result:** No rows (all rules must have TARGETS relationships)

---

### 3.2 Verify All CompatibilityRule Nodes Have HAS_CONSTRAINT Relationships
```cypher
MATCH (r:CompatibilityRule)
WHERE NOT (r)-[:HAS_CONSTRAINT]->(:VersionConstraint)
RETURN r.rule_id, r.rule_type;
```

**Expected Result:** No rows (all rules must have HAS_CONSTRAINT relationships)

---

### 3.3 Verify No Orphaned VersionConstraint Nodes
```cypher
MATCH (vc:VersionConstraint)
WHERE NOT (vc)<-[:HAS_CONSTRAINT|:HAS_CONDITION]-(:CompatibilityRule)
RETURN vc.entity_id, vc.entity_name, vc.operator, vc.version_normalized;
```

**Expected Result:** No rows (all VersionConstraint nodes must be connected to rules)

---

### 3.4 Verify No Orphaned Evidence Nodes
```cypher
MATCH (e:Evidence)
WHERE NOT (e)<-[:HAS_EVIDENCE]-(:CompatibilityRule)
RETURN e.evidence_id, e.source_document_id;
```

**Expected Result:** No rows (all Evidence nodes must be connected to rules)

---

### 3.5 Verify No Orphaned Remediation Nodes
```cypher
MATCH (rem:Remediation)
WHERE NOT (rem)<-[:HAS_REMEDIATION]-(:CompatibilityRule)
RETURN rem.remediation_id, rem.target_component_name;
```

**Expected Result:** No rows (all Remediation nodes must be connected to rules)

---

### 3.6 Verify TARGETS Relationships Point to Valid Layer 1 Entities
```cypher
MATCH (r:CompatibilityRule)-[:TARGETS]->(e)
WHERE NOT e:Entity
RETURN r.rule_id, e.entity_id;
```

**Expected Result:** No rows (all TARGETS must point to Entity nodes)

---

### 3.7 Verify All rule_ids Are Unique
```cypher
MATCH (r:CompatibilityRule)
WITH r.rule_id AS rule_id, count(r) AS count
WHERE count > 1
RETURN rule_id, count;
```

**Expected Result:** No rows (all rule_ids must be unique)

---

### 3.8 Verify All evidence_ids Are Unique
```cypher
MATCH (e:Evidence)
WITH e.evidence_id AS evidence_id, count(e) AS count
WHERE count > 1
RETURN evidence_id, count;
```

**Expected Result:** No rows (all evidence_ids must be unique)

---

### 3.9 Verify All remediation_ids Are Unique
```cypher
MATCH (rem:Remediation)
WITH rem.remediation_id AS remediation_id, count(rem) AS count
WHERE count > 1
RETURN remediation_id, count;
```

**Expected Result:** No rows (all remediation_ids must be unique)

---

## 4. Sample Data Queries

### 4.1 Show Sample CompatibilityRule Nodes
```cypher
MATCH (r:CompatibilityRule)
RETURN r.rule_id, r.rule_type, r.predicate, r.severity, r.approval_status
LIMIT 5;
```

---

### 4.2 Show Sample VersionConstraint Nodes
```cypher
MATCH (vc:VersionConstraint)
RETURN vc.entity_id, vc.entity_name, vc.operator, vc.version_normalized, vc.requirement_kind
LIMIT 10;
```

---

### 4.3 Show Sample Evidence Nodes
```cypher
MATCH (e:Evidence)
RETURN e.evidence_id, e.source_document_id, e.source_chunk_id, e.verification_status
LIMIT 5;
```

---

### 4.4 Show Sample Remediation Nodes
```cypher
MATCH (rem:Remediation)
RETURN rem.remediation_id, rem.remediation_type, rem.target_component_name, rem.target_version
LIMIT 5;
```

---

## 5. Graph Traversal Queries

### 5.1 Show Complete Rule Graph for a Single Rule
```cypher
MATCH (r:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[rel]->(n)
RETURN r.rule_id, type(rel) AS relationship_type, labels(n) AS node_labels, n
LIMIT 25;
```

---

### 5.2 Show Rule with All Dependencies
```cypher
MATCH path = (r:CompatibilityRule {rule_id: "CRULE-AEADF7F483FE03B6-001"})-[:TARGETS|HAS_CONSTRAINT|HAS_CONDITION|HAS_EVIDENCE|HAS_REMEDIATION*]->(n)
RETURN path;
```

---

### 5.3 Show All Rules Targeting a Specific Entity
```cypher
MATCH (r:CompatibilityRule)-[:TARGETS]->(:Entity {entity_id: "FW-001"})
RETURN r.rule_id, r.rule_type, r.predicate, r.severity;
```

---

### 5.4 Show All Rules with Evidence from a Specific Document
```cypher
MATCH (r:CompatibilityRule)-[:HAS_EVIDENCE]->(:Evidence {source_document_id: "DOC-CA114A84AE60"})
RETURN r.rule_id, r.rule_type, r.severity;
```

---

### 5.5 Show Rules by Predicate Type
```cypher
MATCH (r:CompatibilityRule)
RETURN r.predicate, count(r) AS rule_count
ORDER BY rule_count DESC;
```

---

### 5.6 Show Rules by Severity
```cypher
MATCH (r:CompatibilityRule)
RETURN r.severity, count(r) AS rule_count
ORDER BY rule_count DESC;
```

---

### 5.7 Show Rules by Rule Type
```cypher
MATCH (r:CompatibilityRule)
RETURN r.rule_type, count(r) AS rule_count
ORDER BY rule_count DESC;
```

---

## 6. Cross-Layer Integration Queries

### 6.1 Verify Layer 1 Entity References Exist
```cypher
MATCH (r:CompatibilityRule)-[:TARGETS]->(e:Entity)
RETURN count(r) AS rules_with_valid_targets;
```

**Expected Result:** 11 (all rules should have valid Layer 1 targets)

---

### 6.2 Show Rules by Layer 1 Entity
```cypher
MATCH (r:CompatibilityRule)-[:TARGETS]->(e:Entity)
RETURN e.entity_id, e.name, count(r) AS rule_count
ORDER BY rule_count DESC;
```

---

### 6.3 Show Version Constraints by Entity Kind
```cypher
MATCH (vc:VersionConstraint)
RETURN vc.entity_kind, count(vc) AS constraint_count
ORDER BY constraint_count DESC;
```

---

## 7. Comprehensive Validation Query

### 7.1 Full Validation Summary
```cypher
// Node counts
MATCH (cr:CompatibilityRule) WITH count(cr) AS cr_count
MATCH (vc:VersionConstraint) WITH cr_count, count(vc) AS vc_count
MATCH (ev:Evidence) WITH cr_count, vc_count, count(ev) AS ev_count
MATCH (rem:Remediation) WITH cr_count, vc_count, ev_count, count(rem) AS rem_count

// Relationship counts
MATCH ()-[t:TARGETS]->() WITH cr_count, vc_count, ev_count, rem_count, count(t) AS targets_count
MATCH ()-[hc:HAS_CONSTRAINT]->() WITH cr_count, vc_count, ev_count, rem_count, targets_count, count(hc) AS has_constraint_count
MATCH ()-[hcond:HAS_CONDITION]->() WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, count(hcond) AS has_condition_count
MATCH ()-[hev:HAS_EVIDENCE]->() WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, has_condition_count, count(hev) AS has_evidence_count
MATCH ()-[hr:HAS_REMEDIATION]->() WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, has_condition_count, has_evidence_count, count(hr) AS has_remediation_count

// Integrity checks
MATCH (r:CompatibilityRule) WHERE NOT (r)-[:TARGETS]->(:Entity) WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, has_condition_count, has_evidence_count, has_remediation_count, count(r) AS rules_without_targets
MATCH (r:CompatibilityRule) WHERE NOT (r)-[:HAS_CONSTRAINT]->(:VersionConstraint) WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, has_condition_count, has_evidence_count, has_remediation_count, rules_without_targets, count(r) AS rules_without_constraints
MATCH (vc:VersionConstraint) WHERE NOT (vc)<-[:HAS_CONSTRAINT|:HAS_CONDITION]-(:CompatibilityRule) WITH cr_count, vc_count, ev_count, rem_count, targets_count, has_constraint_count, has_condition_count, has_evidence_count, has_remediation_count, rules_without_targets, rules_without_constraints, count(vc) AS orphaned_constraints

RETURN {
  compatibility_rule_count: cr_count,
  version_constraint_count: vc_count,
  evidence_count: ev_count,
  remediation_count: rem_count,
  targets_count: targets_count,
  has_constraint_count: has_constraint_count,
  has_condition_count: has_condition_count,
  has_evidence_count: has_evidence_count,
  has_remediation_count: has_remediation_count,
  rules_without_targets: rules_without_targets,
  rules_without_constraints: rules_without_constraints,
  orphaned_constraints: orphaned_constraints
} AS validation_summary;
```

**Expected Result:**
```json
{
  "compatibility_rule_count": 11,
  "version_constraint_count": 33-44,
  "evidence_count": 11,
  "remediation_count": 11,
  "targets_count": 11,
  "has_constraint_count": 11,
  "has_condition_count": 11-22,
  "has_evidence_count": 11,
  "has_remediation_count": 11,
  "rules_without_targets": 0,
  "rules_without_constraints": 0,
  "orphaned_constraints": 0
}
```

---

## 8. Performance and Index Validation

### 8.1 Check if Constraints Exist
```cypher
SHOW CONSTRAINTS;
```

**Expected Constraints:**
- compatibility_rule_rule_id_unique on :CompatibilityRule(rule_id)
- evidence_evidence_id_unique on :Evidence(evidence_id)
- remediation_remediation_id_unique on :Remediation(remediation_id)

---

### 8.2 Check if Indexes Exist
```cypher
SHOW INDEXES;
```

**Expected Indexes:**
- version_constraint_composite on :VersionConstraint(entity_id, operator, version_normalized)
- entity_entity_id on :Entity(entity_id)
- compatibility_rule_rule_type on :CompatibilityRule(rule_type)
- compatibility_rule_predicate on :CompatibilityRule(predicate)
- compatibility_rule_severity on :CompatibilityRule(severity)
- compatibility_rule_approval_status on :CompatibilityRule(approval_status)

---

## 9. Data Quality Queries

### 9.1 Check for Missing Required Properties
```cypher
MATCH (r:CompatibilityRule)
WHERE r.rule_id IS NULL OR r.rule_type IS NULL OR r.predicate IS NULL OR r.severity IS NULL
RETURN r.rule_id, r.rule_type, r.predicate, r.severity;
```

**Expected Result:** No rows

---

### 9.2 Check for Invalid Confidence Scores
```cypher
MATCH (r:CompatibilityRule)
WHERE r.confidence < 0.0 OR r.confidence > 1.0
RETURN r.rule_id, r.confidence;
```

**Expected Result:** No rows

---

### 9.3 Check for Invalid Timestamps
```cypher
MATCH (r:CompatibilityRule)
WHERE NOT r.created_timestamp =~ '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2}$'
RETURN r.rule_id, r.created_timestamp;
```

**Expected Result:** No rows

---

## 10. Post-Import Verification Checklist

Use the following queries to verify a successful import:

- [ ] CompatibilityRule count = 11
- [ ] VersionConstraint count = 33-44
- [ ] Evidence count = 11
- [ ] Remediation count = 11
- [ ] TARGETS relationships = 11
- [ ] HAS_CONSTRAINT relationships = 11
- [ ] HAS_CONDITION relationships = 11-22
- [ ] HAS_EVIDENCE relationships = 11
- [ ] HAS_REMEDIATION relationships = 11
- [ ] No rules without TARGETS
- [ ] No rules without HAS_CONSTRAINT
- [ ] No orphaned VersionConstraint nodes
- [ ] No orphaned Evidence nodes
- [ ] No orphaned Remediation nodes
- [ ] All TARGETS point to valid Entity nodes
- [ ] All rule_ids are unique
- [ ] All evidence_ids are unique
- [ ] All remediation_ids are unique
- [ ] All required properties present
- [ ] All confidence scores valid (0.0-1.0)
- [ ] All timestamps valid ISO 8601 format
