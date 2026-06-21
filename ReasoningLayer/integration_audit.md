# ReasoningLayer Integration Audit

Generated: 2026-06-21  
Scope: Existing `ReasoningLayer` only  
Constraint: No code files modified

## 1. Current End-to-End Flow

Current active production-style path:

```text
Question
  → QueryUnderstandingService
  → QueryParser
  → IntentClassifier + EntityExtractor + QueryRouter
  → EvidenceService
  → EvidenceAggregator
  → EvidenceCollector
  → QdrantRetriever and/or Neo4jRetriever
  → EvidenceRanker
  → EvidenceGraphBuilder
  → RAGPipeline
  → ResponseOrchestrator
  → RootCauseChain or RecommendationChain
  → LLMService
  → LlamaIndex Ollama LLM
```

Primary active entry point:

- `ReasoningLayer/llm/orchestrator/rag_pipeline.py`

The active `RAGPipeline.run(question)` method performs:

1. `QueryUnderstandingService().understand(question)`
2. `EvidenceService().process(query_plan)`
3. `ResponseOrchestrator().generate(question, evidence_package, intent)`
4. `AnswerValidator().validate(answer, evidence_package)`

Supporting execution wrapper:

- `ReasoningLayer/evaluation/execution/query_execution_engine.py`

This instantiates `RAGPipeline(offline=False)` and is therefore the main evaluation-time path for live Qdrant / Neo4j retrieval.

## 2. Files That Currently Call Qdrant

### Active evidence path

- `ReasoningLayer/evidence_aggregation/evidence_collector.py`
  - Instantiates and calls `QdrantRetriever`.
  - Uses Qdrant for Layer 1 domain evidence and Layer 3 compatibility evidence.

- `ReasoningLayer/evidence_aggregation/qdrant_retriever.py`
  - Main Qdrant retrieval implementation.
  - Calls Qdrant through `QdrantConnector.search()` and `QdrantConnector.scroll()`.
  - Searches:
    - `kb_domain_layer`
    - `kb_compatibility_layer`

- `ReasoningLayer/evidence_aggregation/connectors/qdrant_connector.py`
  - Direct Qdrant client wrapper.
  - Imports `QdrantClient`.
  - Performs `query_points`, `scroll`, and collection existence checks.

### LLM infrastructure / health path

- `ReasoningLayer/llm/connectors/qdrant_connector.py`
  - Qdrant health and collection validation connector.

- `ReasoningLayer/llm/validate_infrastructure.py`
  - Calls `QdrantConnector().health_check()`.

- `ReasoningLayer/llm/tests/test_qdrant_connection.py`
  - Tests Qdrant reachability and required collections.

## 3. Files That Currently Call Neo4j

### Active evidence path

- `ReasoningLayer/evidence_aggregation/evidence_collector.py`
  - Instantiates and calls `Neo4jRetriever`.
  - Uses Neo4j for Layer 2 inventory evidence.

- `ReasoningLayer/evidence_aggregation/neo4j_retriever.py`
  - Main inventory retriever.
  - Retrieves:
    - device node
    - installed BIOS
    - installed firmware
    - installed OS
    - installed drivers
    - installed security agents
    - installed management agents
    - device relationships
    - fleet devices

- `ReasoningLayer/evidence_aggregation/connectors/neo4j_connector.py`
  - Direct Neo4j driver wrapper.
  - Imports `GraphDatabase`.
  - Reads `NEO4J_URI`, `NEO4J_USERNAME` / `NEO4J_USER`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`.

### LLM infrastructure / health path

- `ReasoningLayer/llm/connectors/neo4j_connector.py`
  - Neo4j connectivity, stats, and query connector.

- `ReasoningLayer/llm/validate_infrastructure.py`
  - Calls `Neo4jConnector().health_check()`.

- `ReasoningLayer/llm/tests/test_neo4j_connection.py`
  - Tests Neo4j connection and query execution.

## 4. Files That Currently Do Not Use Neo4j But Should

These files are in or near the active reasoning path and would benefit from direct or mediated Neo4j access.

### `ReasoningLayer/root_cause_engine/violation_detector.py`

Current role:

- Detects violations from the evidence package.

Gap:

- It only sees already-collected evidence.
- It does not directly query Neo4j for device state, installed components, relationship context, or observed inventory deltas.

Recommended Neo4j use:

- Use Neo4j inventory facts to confirm actual installed state before declaring a root cause.
- Query `Device → installed component` paths when evidence lacks version/configuration details.

### `ReasoningLayer/root_cause_engine/root_cause_analyzer.py`

Current role:

- Produces RCA findings from evidence.

Gap:

- Device identity is extracted from evidence package or regex fallback.
- It does not enrich findings with graph context such as impacted neighboring components, vendor, model, inventory snapshot, or relationship paths.

Recommended Neo4j use:

- Add graph-context enrichment after violation detection:
  - device model
  - vendor
  - installed BIOS / firmware / OS / drivers
  - direct graph relationships
  - affected component paths

### `ReasoningLayer/root_cause_engine/recommendation_engine.py`

Current role:

- Enriches RCA output with recommendations.

Gap:

- Recommendations are not grounded in live installed inventory state.

Recommended Neo4j use:

- Query current installed versions and vendor/model before suggesting upgrade/remediation.
- Validate whether recommended target component is relevant to the device.

### `ReasoningLayer/llm/orchestrator/response_orchestrator.py`

Current role:

- Selects the answer-generation chain by intent.

Gap:

- It trusts the evidence package as-is.
- It does not enforce required Layer 2 evidence for device-specific intents.

Recommended Neo4j use:

- Not direct Cypher, but should enforce that `RootCauseAnalysis`, `ComplianceStatus`, `RiskAssessment`, `FleetAnalysis`, `DeviceInvestigation`, and `UpgradeImpactAnalysis` include Layer 2 inventory evidence before generation.

### `ReasoningLayer/llm/validation/answer_validator.py`

Current role:

- Validates generated answers against evidence.

Gap:

- Does not independently verify device/component claims against Neo4j.

Recommended Neo4j use:

- For answers mentioning device state or installed versions, validate claims against Neo4j inventory evidence or call a Neo4j-backed fact checker.

### `ReasoningLayer/evaluation/scoring/hallucination_detector.py`

Current role:

- Detects hallucination risk.

Gap:

- Does not query authoritative graph facts.

Recommended Neo4j use:

- For inventory claims, check whether claimed device/component/version exists in Neo4j.

## 5. Active Retrieval Pipeline

The active retrieval pipeline is:

```text
RAGPipeline
  → EvidenceService
  → EvidenceAggregator
  → EvidenceCollector
  → QdrantRetriever for Layer1 and Layer3
  → Neo4jRetriever for Layer2
  → EvidenceRanker
  → EvidenceGraphBuilder
```

Active files:

- `ReasoningLayer/llm/orchestrator/rag_pipeline.py`
- `ReasoningLayer/evidence_aggregation/evidence_service.py`
- `ReasoningLayer/evidence_aggregation/evidence_aggregator.py`
- `ReasoningLayer/evidence_aggregation/evidence_collector.py`
- `ReasoningLayer/evidence_aggregation/qdrant_retriever.py`
- `ReasoningLayer/evidence_aggregation/neo4j_retriever.py`
- `ReasoningLayer/evidence_aggregation/evidence_ranker.py`
- `ReasoningLayer/evidence_aggregation/evidence_graph_builder.py`

Layer routing:

- Layer 1 → Qdrant domain collection
- Layer 2 → Neo4j inventory graph
- Layer 3 → Qdrant compatibility collection

## 6. Active Orchestrator

The active orchestrator is:

- `ReasoningLayer/llm/orchestrator/response_orchestrator.py`

Class:

- `ResponseOrchestrator`

Selection logic:

- `RecommendationRequest` → `RecommendationChain`
- all other intents → `RootCauseChain`

Supported intent set includes:

- `ConceptExplanation`
- `RootCauseAnalysis`
- `RecommendationRequest`
- `RiskAssessment`
- `FleetAnalysis`
- `DependencyAnalysis`
- `CompatibilityInquiry`

Important note:

- `PreventionRequest` appears in `TEMPLATE_BY_INTENT`, but not in `SUPPORTED_INTENTS`.
- `SUPPORTED_INTENTS` is not enforced in `generate()`, so the mismatch does not currently block execution.

## 7. Active Answer Generation Path

Current active answer generation path:

```text
ResponseOrchestrator.generate()
  → select prompt template
  → RootCauseChain or RecommendationChain
  → GroundedChain._call()
  → CitationBuilder.format_evidence()
  → LLMService.generate_response()
  → LlamaIndex Ollama complete()
  → parse_json_response()
  → canonicalize citations
```

Active files:

- `ReasoningLayer/llm/orchestrator/response_orchestrator.py`
- `ReasoningLayer/llm/chains/root_cause_chain.py`
- `ReasoningLayer/llm/chains/recommendation_chain.py`
- `ReasoningLayer/llm/chains/common.py`
- `ReasoningLayer/llm/services/llm_service.py`
- `ReasoningLayer/llm/connectors/ollama_connector.py`
- `ReasoningLayer/llm/validation/citation_builder.py`

LLM implementation:

- `ReasoningLayer/llm/services/llm_service.py`
- Uses `llama_index.llms.ollama.Ollama`
- Default model config: `llama3.1:8b`

Generation behavior:

- If no citations/evidence are available, `GroundedChain` abstains with `"Insufficient evidence"`.
- If LLM generation fails, `GroundedChain` returns failure fields instead of raising downstream.
- Expected LLM response is JSON.

## 8. Missing Integration Points

### 8.1 Neo4j label and relationship mismatch

Current `Neo4jRetriever` queries:

- `(:Device)-[:HAS_BIOS]->(:BIOS)`
- `(:Device)-[:HAS_FIRMWARE]->(:Firmware)`
- `(:Device)-[:HAS_OS]->(:OperatingSystem)`
- `(:Device)-[:HAS_DRIVER]->(:Driver)`
- `(:Device)-[:HAS_SECURITY_AGENT]->(:SecurityAgent)`
- `(:Device)-[:HAS_MANAGEMENT_AGENT]->(:ManagementAgent)`

Current InventoryLayer Neo4j import package creates:

- `:Device`
- `:InstalledBIOS`
- `:InstalledFirmware`
- `:InstalledOS`
- `:InstalledDriver`
- `:Vendor`

And relationships:

- `HAS_BIOS`
- `HAS_FIRMWARE`
- `RUNS_OS`
- `HAS_DRIVER`
- `BELONGS_TO_VENDOR`

Impact:

- Layer 2 retrieval will miss BIOS, firmware, OS, and driver evidence even if the graph is loaded, because labels and relationship names do not match.
- OS retrieval is especially mismatched: retriever uses `HAS_OS` but import uses `RUNS_OS`.

### 8.2 Security agent and management tool import gap

The active retriever has methods for:

- `get_installed_security_agents()`
- `get_installed_management_agents()`

But the current InventoryLayer Neo4j import package does not include:

- `security_agent_nodes.csv`
- `management_tool_nodes.csv`
- `HAS_SECURITY_AGENT` relationships
- `HAS_MANAGEMENT_TOOL` relationships

Impact:

- Security and management evidence cannot be retrieved from Neo4j even though the schema and ontology define those concepts.

### 8.3 Layer 3 compatibility rules are only retrieved from Qdrant

Current compatibility retrieval:

- `EvidenceCollector._collect_compatibility()`
- `QdrantRetriever.search_compatibility()`
- `QdrantRetriever.retrieve_by_rule()`
- `QdrantRetriever.retrieve_by_version()`

Gap:

- No Neo4j traversal is used for compatibility rule relationships, dependency chains, affected components, or rule graph context.

Impact:

- RAG can retrieve semantically similar rule documents but cannot reliably traverse structured compatibility paths.

### 8.4 Query understanding routes Layer 2, but entity extraction may not normalize device IDs

`EntityExtractor` extracts device-like strings such as:

- `Laptop001`
- `Device999`
- `ServerABC`

But inventory import uses device IDs such as:

- `DEV-DELL-0001`
- `DEV-HP-0002`

Impact:

- Device-specific Neo4j lookups may fail when natural-language device names do not match `Device.device_id`.

### 8.5 Evidence aggregation has no fallback from missing Neo4j evidence

If Neo4j is unavailable or returns no Layer 2 evidence:

- `Neo4jConnector.run()` returns `[]`
- `Neo4jRetriever` returns empty evidence lists
- `GroundedChain` may abstain if there are no citations

Gap:

- There is no explicit diagnostic evidence saying “Neo4j unavailable” or “device not found.”

Impact:

- The LLM may see partial Qdrant-only evidence without an explicit explanation that inventory evidence is missing.

### 8.6 RAG path bypasses the dedicated Root Cause Engine

There are two root-cause paths:

1. RAG answer path:
   - `RAGPipeline`
   - `ResponseOrchestrator`
   - `RootCauseChain`
   - LLM

2. Deterministic RCA engine path:
   - `RootCauseService`
   - `RootCauseAnalyzer`
   - `ViolationDetector`
   - `RiskAssessor`
   - `RecommendationEngine`

Gap:

- The active RAG answer path does not call `RootCauseService` or `RootCauseAnalyzer`.

Impact:

- LLM root-cause answers may not use deterministic violation detection and risk scoring already implemented in the RCA engine.

### 8.7 No FastAPI/API boundary in ReasoningLayer

No FastAPI endpoint was detected for:

- query understanding
- evidence retrieval
- RAG answer generation
- root cause analysis
- graph verification

Impact:

- ReasoningLayer is currently script/class-driven, not exposed as an API layer.

## 9. Recommended Neo4j Insertion Points

### Priority 1: Fix `Neo4jRetriever` to match loaded graph schema

File:

- `ReasoningLayer/evidence_aggregation/neo4j_retriever.py`

Recommended query alignment:

- `(:Device)-[:HAS_BIOS]->(:InstalledBIOS)`
- `(:Device)-[:HAS_FIRMWARE]->(:InstalledFirmware)`
- `(:Device)-[:RUNS_OS]->(:InstalledOS)`
- `(:Device)-[:HAS_DRIVER]->(:InstalledDriver)`
- `(:Device)-[:BELONGS_TO_VENDOR]->(:Vendor)`

Reason:

- This is the immediate blocker for Layer 2 inventory evidence retrieval.

### Priority 2: Add security and management nodes to the inventory graph

Recommended import additions:

- `security_agent_nodes.csv`
- `management_tool_nodes.csv`
- `has_security_agent_relationships.csv`
- `has_management_tool_relationships.csv`

Recommended retriever alignment:

- `(:Device)-[:HAS_SECURITY_AGENT]->(:InstalledSecurityAgent)`
- `(:Device)-[:HAS_MANAGEMENT_TOOL]->(:InstalledManagementTool)`

Reason:

- These are part of the Inventory Ontology and schema but not currently represented in the Neo4j import package.

### Priority 3: Add device identity resolution before Neo4j lookup

Recommended insertion point:

- `ReasoningLayer/query_understanding/entity_extractor.py`
- or a new resolver called by `EvidenceCollector._collect_inventory()`

Recommended behavior:

- Resolve natural names like `Laptop001` to Neo4j `device_id`.
- Support lookup by:
  - `device_id`
  - `device_name`
  - hostname aliases
  - inventory name

Reason:

- Query extraction currently produces human-facing names, while graph lookup uses `device_id`.

### Priority 4: Add explicit Neo4j retrieval diagnostics

Recommended insertion point:

- `ReasoningLayer/evidence_aggregation/neo4j_retriever.py`
- `ReasoningLayer/evidence_aggregation/evidence_collector.py`

Recommended behavior:

- Emit diagnostic evidence when:
  - Neo4j is unavailable
  - device not found
  - no Layer 2 inventory returned for a Layer 2-routed query

Reason:

- Prevents silent loss of inventory context.

### Priority 5: Use Neo4j for compatibility traversal when Layer 3 graph exists

Recommended insertion point:

- `ReasoningLayer/evidence_aggregation/evidence_collector.py`
- new `CompatibilityGraphRetriever`

Recommended behavior:

- Keep Qdrant for semantic rule discovery.
- Add Neo4j traversal for:
  - rule dependencies
  - affected components
  - compatibility paths
  - remediation paths
  - version constraints

Reason:

- Qdrant is good for semantic recall; Neo4j is required for deterministic relationship traversal.

### Priority 6: Bridge RAGPipeline to RootCauseService for root-cause intents

Recommended insertion point:

- `ReasoningLayer/llm/orchestrator/response_orchestrator.py`
- or `ReasoningLayer/llm/orchestrator/rag_pipeline.py`

Recommended behavior:

- For `RootCauseAnalysis`, call deterministic RCA engine before LLM generation.
- Pass RCA findings into `RootCauseChain` as structured evidence.

Reason:

- Combines deterministic graph/evidence reasoning with grounded LLM explanation.

## Final Assessment

Current integration status:

- Query understanding: present and active
- Retrieval routing: present and active
- Qdrant retrieval: present and active for Layer 1 and Layer 3
- Neo4j retrieval: present and intended for Layer 2, but likely schema-mismatched against current InventoryLayer import files
- Evidence aggregation: present and active
- RAG orchestration: present and active
- LLM generation: present and active through LlamaIndex + Ollama
- Dedicated RCA engine: present, but not part of the active RAG answer path

Overall conclusion:

The ReasoningLayer has a coherent end-to-end architecture, but Layer 2 Neo4j integration is not fully wired to the current inventory graph schema. The most important next step is to align `Neo4jRetriever` with the actual imported node labels and relationship names, then add missing security/management graph coverage and device identity resolution.

