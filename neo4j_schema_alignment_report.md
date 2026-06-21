# Neo4jRetriever Schema Alignment Report

Generated: 2026-06-21  
Compared file: `ReasoningLayer/evidence_aggregation/neo4j_retriever.py`  
Database inspected: `neo4j`  
Mode: Read-only audit; no code modified

## Executive Summary

`Neo4jRetriever` is not aligned with the actual live Neo4j graph schema.

The retriever currently expects direct component relationships such as:

```cypher
(:Device)-[:HAS_BIOS]->(:BIOS)
(:Device)-[:HAS_FIRMWARE]->(:Firmware)
(:Device)-[:HAS_OS]->(:OperatingSystem)
(:Device)-[:HAS_DRIVER]->(:Driver)
```

The actual graph uses the existing Layer 2 architecture:

```cypher
(:Device)-[:HAS_COMPONENT]->(:ComponentInstance)-[:INSTANCE_OF]->(:Entity)
```

Domain category labels such as `Firmware`, `Driver`, `OperatingSystem`, `ManagementTool`, and `SecurityComponent` exist on `Entity` nodes, not on installed component nodes.

## Actual Graph Summary

### Node Labels

Observed labels:

- `Device`
- `ComponentInstance`
- `Entity`
- `Firmware`
- `Driver`
- `OperatingSystem`
- `HardwareComponent`
- `ManagementTool`
- `SecurityComponent`
- `CompatibilityRule`
- `VersionConstraint`
- `Evidence`
- `Remediation`

Not observed:

- `BIOS`
- `Vendor`
- `SecurityAgent`
- `ManagementAgent`

### Relationship Types

Observed relationship types:

- `HAS_COMPONENT`
- `INSTANCE_OF`
- `HAS_CONDITION`
- `HAS_CONSTRAINT`
- `HAS_EVIDENCE`
- `HAS_REMEDIATION`
- `TARGETS`

Not observed:

- `HAS_BIOS`
- `HAS_FIRMWARE`
- `HAS_OS`
- `RUNS_OS`
- `HAS_DRIVER`
- `HAS_SECURITY_AGENT`
- `HAS_MANAGEMENT_AGENT`
- `HAS_MANAGEMENT_TOOL`
- `BELONGS_TO_VENDOR`

### Relevant Counts

```text
Device nodes:              20
ComponentInstance nodes:   262
Entity nodes:              69
HAS_COMPONENT:             262
INSTANCE_OF:               222
```

Component instance counts:

```text
agent:              30
bios:               20
driver:             24
firmware:           20
management_tool:    20
os:                 20
tpm:                10
```

## Alignment Matrix

| Area | Current Query | Actual Graph | Required Fix |
|---|---|---|---|
| BIOS | `MATCH (d:Device {device_id: $id})-[:HAS_BIOS]->(b:BIOS) RETURN b` | BIOS is stored as `ComponentInstance` with `component_type = "bios"`, connected by `(:Device)-[:HAS_COMPONENT]->(:ComponentInstance)-[:INSTANCE_OF]->(:Entity:Firmware {name: "BIOS"})`. There is no `:BIOS` label and no `HAS_BIOS` relationship. | Query through `HAS_COMPONENT` and filter `ComponentInstance.component_type = "bios"`. Optionally return the mapped `Entity`. |
| Firmware | `MATCH (d:Device {device_id: $id})-[:HAS_FIRMWARE]->(f:Firmware) RETURN f` | Firmware instances are `ComponentInstance` nodes with `component_type = "firmware"`. They map via `INSTANCE_OF` to `Entity:Firmware`, e.g. `Intel Management Engine Firmware`, `Lifecycle Controller Firmware`. There is no `HAS_FIRMWARE` relationship from `Device` to `Firmware`. | Query `Device -> HAS_COMPONENT -> ComponentInstance`, filter `component_type = "firmware"`, and optionally match `INSTANCE_OF -> Entity:Firmware`. |
| OS | `MATCH (d:Device {device_id: $id})-[:HAS_OS]->(o:OperatingSystem) RETURN o` | OS instances are `ComponentInstance` nodes with `component_type = "os"`, mapped to `Entity:OperatingSystem`, e.g. `Windows`, `VMware ESXi`, `Ubuntu`. There is no `HAS_OS` relationship. There is also no `RUNS_OS` relationship in the live graph. | Query `HAS_COMPONENT` with `component_type = "os"` and optionally `INSTANCE_OF -> Entity:OperatingSystem`. |
| Drivers | `MATCH (d:Device {device_id: $id})-[:HAS_DRIVER]->(dr:Driver) RETURN dr` | Driver instances are `ComponentInstance` nodes with `component_type = "driver"`, mapped to `Entity:Driver`, e.g. `Network Driver`, `Intel AX211 Wi-Fi Driver`, `NVIDIA RTX Workstation Driver`. There is no `HAS_DRIVER` relationship in the live graph. | Query `HAS_COMPONENT` with `component_type = "driver"` and optionally `INSTANCE_OF -> Entity:Driver`. |
| Vendor | No dedicated vendor retrieval method. Vendor is only indirectly present in component evidence if returned nodes contain `vendor`. | There is no `Vendor` label and no `BELONGS_TO_VENDOR` relationship. Vendor appears as properties on `ComponentInstance.vendor` and as `Device.manufacturer`. | Query vendor from `Device.manufacturer` and `ComponentInstance.vendor`. If a normalized vendor graph is desired, create `Vendor` nodes later, but current retriever should read existing properties. |
| Security Agent | `MATCH (d:Device {device_id:$id})-[:HAS_SECURITY_AGENT]->(s:SecurityAgent) RETURN s` | No `SecurityAgent` label and no `HAS_SECURITY_AGENT` relationship. Security-related installed records appear mainly as `ComponentInstance` nodes with `component_type = "agent"` mapped to `Entity:SecurityComponent` for `EDR Agent`. `tpm` components also map to `SecurityComponent`, but those are not security agents. | Query `HAS_COMPONENT` where `component_type = "agent"` and `INSTANCE_OF` target has label `SecurityComponent`. Keep TPM separate unless intentionally treated as security component evidence. |
| Management Tool | `MATCH (d:Device {device_id:$id})-[:HAS_MANAGEMENT_AGENT]->(m:ManagementAgent) RETURN m` | No `ManagementAgent` label and no `HAS_MANAGEMENT_AGENT` relationship. Management tools appear as `ComponentInstance` nodes with `component_type = "management_tool"` mapped to `Entity:ManagementTool`. Some `agent` components such as `Endpoint Agent` also map to `ManagementTool`. | Query `HAS_COMPONENT` where `component_type = "management_tool"` or where `component_type = "agent"` and mapped entity has label `ManagementTool`. Relationship name should not be `HAS_MANAGEMENT_AGENT` for this graph. |

## Required Query Fixes

These are the Cypher shapes the retriever should use to match the actual graph.

### BIOS

Current query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_BIOS]->(b:BIOS)
RETURN b
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type = "bios"
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity)
RETURN c AS component, e AS entity
```

Expected evidence source:

- `component.component_name`
- `component.version_raw`
- `component.version_normalized`
- `component.vendor`
- `entity.name`

### Firmware

Current query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_FIRMWARE]->(f:Firmware)
RETURN f
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type = "firmware"
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity:Firmware)
RETURN c AS component, e AS entity
```

Observed mapped firmware entities:

- `Intel Management Engine Firmware`
- `Lifecycle Controller Firmware`

### OS

Current query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_OS]->(o:OperatingSystem)
RETURN o
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type = "os"
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity:OperatingSystem)
RETURN c AS component, e AS entity
```

Observed mapped OS entities:

- `Windows`
- `VMware ESXi`
- `Ubuntu`

### Drivers

Current query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_DRIVER]->(dr:Driver)
RETURN dr
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type = "driver"
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity:Driver)
RETURN c AS component, e AS entity
```

Observed mapped driver entities:

- `Network Driver`
- `Intel AX211 Wi-Fi Driver`
- `NVIDIA RTX Workstation Driver`

### Vendor

Current query:

```text
No dedicated vendor query exists in Neo4jRetriever.
```

Actual graph:

```text
No :Vendor nodes.
No BELONGS_TO_VENDOR relationships.
Vendor is stored as properties:
  Device.manufacturer
  ComponentInstance.vendor
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})
OPTIONAL MATCH (d)-[:HAS_COMPONENT]->(c:ComponentInstance)
RETURN
  d.manufacturer AS device_vendor,
  collect(DISTINCT c.vendor) AS component_vendors
```

Observed vendor-like properties include:

- `Dell`
- `Lenovo`
- `HP`
- `Intel`
- `Microsoft`
- `VMware`
- `Ubuntu`
- `NVIDIA`
- `SentinelOne`
- `CompatIQ`

### Security Agent

Current query:

```cypher
MATCH (d:Device {device_id:$id})-[:HAS_SECURITY_AGENT]->(s:SecurityAgent)
RETURN s
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type = "agent"
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity:SecurityComponent)
WHERE e IS NOT NULL
RETURN c AS component, e AS entity
```

Observed mapped security-agent-like entity:

- `EDR Agent`

Important distinction:

- `TPM` is also a `SecurityComponent`, but it appears as `component_type = "tpm"`, not as an agent.

### Management Tool

Current query:

```cypher
MATCH (d:Device {device_id:$id})-[:HAS_MANAGEMENT_AGENT]->(m:ManagementAgent)
RETURN m
```

Required query:

```cypher
MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
WHERE c.component_type IN ["management_tool", "agent"]
OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity:ManagementTool)
WHERE e IS NOT NULL
RETURN c AS component, e AS entity
```

Observed mapped management entities:

- `Endpoint Manager`
- `Endpoint Agent`

## Additional Retriever Issue

`get_device_relationships()` currently runs:

```cypher
MATCH (d:Device {device_id: $id})-[r]-(n)
RETURN type(r) AS rel, n
```

This query is schema-compatible because it uses any relationship type.

However, the evidence builder uses:

```python
target=str(target.get("id") or target.get("name", ""))
```

Actual `ComponentInstance` nodes typically use:

- `component_instance_id`
- `component_name`
- `component_type`

Required evidence target fallback should include:

```python
component_instance_id
component_name
entity_id
name
```

## Recommended Implementation Strategy

Do not introduce direct installed-component labels unless the graph is redesigned. The current graph architecture is already:

```cypher
Device
  -[:HAS_COMPONENT]->
ComponentInstance
  -[:INSTANCE_OF]->
Entity
```

Therefore the lowest-risk fix is to update `Neo4jRetriever` to:

1. Query `ComponentInstance` nodes by `component_type`.
2. Optionally join to `Entity` using `INSTANCE_OF`.
3. Build evidence from both the instance node and canonical entity node.
4. Treat vendor as a property, not a node, unless a future graph migration adds `Vendor`.

## Final Alignment Status

```text
FAIL
```

Reason:

`Neo4jRetriever` expects a direct installed-component graph schema, but the actual Neo4j graph uses the existing Layer 2 `Device → ComponentInstance → Entity` architecture.

Primary required fix:

Replace direct relationship queries such as `HAS_BIOS`, `HAS_DRIVER`, and `HAS_OS` with `HAS_COMPONENT` queries filtered by `ComponentInstance.component_type` and enriched via `INSTANCE_OF`.

