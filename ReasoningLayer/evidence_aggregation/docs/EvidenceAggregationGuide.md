# Evidence Aggregation Guide

## Architecture

The Evidence Aggregation Layer is Layer 4 Phase 3 of the Dynamic Compatibility &
Configuration Compliance Engine. It converts a Query Understanding query plan into
a unified `EvidencePackage` consumed by the Root Cause Engine, Recommendation
Engine, and Compliance Evaluation Engine.

```
Natural-Language Question
    |
    v
QueryUnderstandingService  (Layer 4 Phase 2)
    |  query_plan: {intent, entities, target_layers, required_action}
    v
EvidenceService
    |
    v
EvidenceAggregator
    |-- EvidenceCollector
    |       |-- QdrantRetriever  --> Layer 1 (domain_knowledge)
    |       |                   --> Layer 3 (compatibility_rules)
    |       \-- Neo4jRetriever   --> Layer 2 (Neo4j inventory)
    |-- EvidenceRanker
    \-- EvidenceGraphBuilder
    |
    v
EvidencePackage
    {query_id, intent, question, entities,
     evidence[], ranked_evidence[], evidence_graph{}, metadata}
```

## Retrieval Flow

1. `EvidenceService.process(question)` calls `QueryUnderstandingService` to
   produce a query plan.
2. `EvidenceAggregator.aggregate(plan)` orchestrates the three sub-steps.
3. `EvidenceCollector.collect(plan)` fans out to:
   - **Layer 1** via `QdrantRetriever.search_domain()` and
     `retrieve_by_entity()` — returns `DomainEvidence`.
   - **Layer 2** via `Neo4jRetriever.get_device()` and component getters —
     returns `InventoryEvidence`.
   - **Layer 3** via `QdrantRetriever.search_compatibility()`,
     `retrieve_by_rule()`, and `retrieve_by_version()` — returns
     `CompatibilityEvidence`, `VersionEvidence`, etc.
4. Duplicates are removed by `evidence_id` (deterministic SHA-256 hash).
5. `EvidenceRanker.rank()` assigns priority and sorts descending by score.
6. `EvidenceGraphBuilder.build()` creates temporary nodes and edges.
7. `EvidencePackage` is returned.

## Qdrant Integration

```python
from ReasoningLayer.evidence_aggregation.connectors.qdrant_connector import QdrantConnector
from ReasoningLayer.evidence_aggregation.qdrant_retriever import QdrantRetriever

connector = QdrantConnector(host="localhost", port=6333)
retriever = QdrantRetriever(connector=connector)

domain_results = retriever.search_domain("BIOS")
compat_results = retriever.search_compatibility("firmware version requirement")
version_results = retriever.retrieve_by_version("BIOS", "6.4.2")
```

Collections:
- `domain_knowledge` — Layer 1 domain entity records
- `compatibility_rules` — Layer 3 candidate rules and constraints

## Neo4j Integration

```python
from ReasoningLayer.evidence_aggregation.connectors.neo4j_connector import Neo4jConnector
from ReasoningLayer.evidence_aggregation.neo4j_retriever import Neo4jRetriever

connector = Neo4jConnector(uri="bolt://localhost:7687",
                           user="neo4j", password="password")
retriever = Neo4jRetriever(connector=connector)

device   = retriever.get_device("Laptop001")
firmware = retriever.get_installed_firmware("Laptop001")
bios     = retriever.get_installed_bios("Laptop001")
os_ev    = retriever.get_installed_os("Laptop001")
drivers  = retriever.get_installed_drivers("Laptop001")
```

## Evidence Ranking

Priority scores (before confidence modifier):

| Evidence Type | Priority | Base Score |
|---|---|---|
| ViolationEvidence | Critical | 100 |
| RiskEvidence | Critical | 100 |
| InventoryEvidence | Highest | 85 |
| CompatibilityEvidence | High | 70 |
| VersionEvidence | High | 70 |
| DependencyEvidence | High | 70 |
| RecommendationEvidence | High | 70 |
| LifecycleEvidence | Medium | 50 |
| DomainEvidence | Medium | 50 |

`final_score = base_score * (0.5 + 0.5 * confidence)`

## Evidence Graph

The `EvidenceGraphBuilder` produces a lightweight in-memory graph:

```json
{
  "node_count": 3,
  "edge_count": 2,
  "nodes": [
    {"node_id": "N-A1B2C3D4", "type": "InventoryEvidence",
     "label": "Laptop001", "properties": {...}},
    {"node_id": "N-E5F6A7B8", "type": "TargetNode",
     "label": "Firmware 3.2", "properties": {}}
  ],
  "edges": [
    {"from": "N-A1B2C3D4", "to": "N-E5F6A7B8",
     "relationship": "HAS_FIRMWARE", "weight": 1.0}
  ]
}
```

## Operation

```powershell
# Run the service
python ReasoningLayer/evidence_aggregation/evidence_service.py \
    "Why is Laptop001 non-compliant?" --offline

# Run tests
python -m pytest ReasoningLayer/evidence_aggregation/tests/ -v

# Run project-wide suite
python -m pytest tests/ ReasoningLayer/ -v
```

## Extension Strategy

1. **New evidence type** — add to `evidence_types.json`, `EVIDENCE_TYPES` set,
   `_TYPE_PRIORITY` in `evidence_ranker.py`, and the priority matrix.
2. **New retriever** — implement `retrieve_*` methods returning `List[Evidence]`
   with correct `evidence_type` and `source_layer`.
3. **New layer** — add connector + retriever, register in `EvidenceCollector`,
   extend routing in query_router_rules.json.
4. **Live Qdrant** — set host/port, ensure collections exist with `entity_name`
   and `confidence` payload fields.
5. **Live Neo4j** — verify node labels (`Device`, `BIOS`, `Firmware`, etc.) and
   relationship types (`HAS_BIOS`, `HAS_FIRMWARE`, etc.) match retriever queries.
