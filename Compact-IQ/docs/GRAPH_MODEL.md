# GRAPH_MODEL — Neo4j

Neo4j stores relationship projections from PostgreSQL. PostgreSQL remains the source of truth.

## Node Labels

| Label | Description |
|---|---|
| `Document` | Source document |
| `Chunk` | Source evidence chunk |
| `Rule` | Approved rule |
| `ConditionSet` | AND/OR group for conditions |
| `Condition` | Individual rule condition |
| `Requirement` | Required target constraint |
| `Device` | Inventory device |
| `ComponentInstance` | Device component state |
| `Violation` | Compliance violation |
| `RemediationStep` | Suggested remediation step |
| `Scan` | Compliance scan run |

## Relationships

```text
(Document)-[:HAS_CHUNK]->(Chunk)
(Rule)-[:EXTRACTED_FROM]->(Chunk)
(Rule)-[:HAS_CONDITION_SET]->(ConditionSet)
(ConditionSet)-[:HAS_CONDITION]->(Condition)
(Rule)-[:HAS_REQUIREMENT]->(Requirement)

(Device)-[:HAS_COMPONENT]->(ComponentInstance)
(Device)-[:VIOLATES]->(Rule)
(Violation)-[:ON_DEVICE]->(Device)
(Violation)-[:CAUSED_BY_RULE]->(Rule)
(Violation)-[:OBSERVED_COMPONENT]->(ComponentInstance)
(Violation)-[:EXPECTED_REQUIREMENT]->(Requirement)
(Violation)-[:REMEDIATED_BY]->(RemediationStep)
(Scan)-[:PRODUCED]->(Violation)
```

## Why ConditionSet Exists

Compound rules must preserve AND/OR logic.

Example:

```text
OS = VMware ESXi 5.1.x
AND HBA = QLogic QLE24xx
AND CPU = Intel Xeon E5-2400 V2
→ BIOS must be >= 02.04.02
```

Do not model this as three independent rules. It must be:

```text
Rule → ConditionSet(AND) → Condition A/B/C
Rule → Requirement
```

## Example Cypher — Create Rule Graph

```cypher
MERGE (r:Rule {rule_id: $rule_id})
SET r.rule_type = $rule_type,
    r.severity = $severity,
    r.confidence_score = $confidence_score

MERGE (cs:ConditionSet {condition_set_id: $condition_set_id})
SET cs.logic = $condition_logic
MERGE (r)-[:HAS_CONDITION_SET]->(cs)

FOREACH (cond IN $conditions |
  MERGE (c:Condition {condition_id: cond.condition_id})
  SET c.component_type = cond.component_type,
      c.component_name = cond.component_name,
      c.operator = cond.operator,
      c.value_normalized = cond.value_normalized,
      c.version_normalized = cond.version_normalized
  MERGE (cs)-[:HAS_CONDITION]->(c)
)

FOREACH (req IN $requirements |
  MERGE (rq:Requirement {requirement_id: req.requirement_id})
  SET rq.component_type = req.component_type,
      rq.component_name = req.component_name,
      rq.operator = req.operator,
      rq.version_normalized = req.version_normalized,
      rq.requirement_kind = req.requirement_kind
  MERGE (r)-[:HAS_REQUIREMENT]->(rq)
)
```

## Example Query — Device Explanation Path

```cypher
MATCH (d:Device {device_id: $device_id})-[:VIOLATES]->(r:Rule)
MATCH (r)-[:HAS_REQUIREMENT]->(req:Requirement)
OPTIONAL MATCH (r)-[:EXTRACTED_FROM]->(chunk:Chunk)<-[:HAS_CHUNK]-(doc:Document)
OPTIONAL MATCH (v:Violation)-[:ON_DEVICE]->(d)
OPTIONAL MATCH (v)-[:REMEDIATED_BY]->(rem:RemediationStep)
RETURN d, r, req, chunk, doc, v, rem
```

## Graph Export for Frontend

Neo4j responses must be converted to `graph_export.schema.json` before sending to the frontend.
