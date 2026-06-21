# Query Understanding Guide

## Architecture

The Query Understanding Layer converts a natural-language endpoint question into an explainable query plan for retrieval and reasoning services.

```text
Question
  -> IntentClassifier
  -> EntityExtractor
  -> QueryRouter
  -> QueryParser
  -> Structured Query Plan
```

`QueryUnderstandingService` is the public boundary. It validates input and returns the unified plan consumed by the Evidence Aggregation Layer, Neo4j and Qdrant retrieval engines, Root Cause Engine, and Recommendation Engine.

The implementation is deterministic and vendor-neutral. Classification decisions come from `query_router_rules.json`, while catalogs provide stable vocabulary for downstream consumers.

## Query Plan

```json
{
  "question": "Why is Laptop001 failing?",
  "intent": "RootCauseAnalysis",
  "confidence": 0.9,
  "intents": [
    {"intent": "RootCauseAnalysis", "confidence": 0.9}
  ],
  "intent_mode": "single",
  "entities": {"device": "Laptop001"},
  "target_layers": ["Layer2", "Layer3"],
  "required_action": "InvestigateViolation"
}
```

`intent` is the highest-ranked intent for simple consumers. `intents` preserves up to three supported interpretations for multi-intent and hybrid questions. `target_layers` is ordered and duplicate-free.

## Intent Model

The 15 intents cover concept explanation, root cause, compliance, recommendations, prevention, risk, dependency, compatibility, violations, fleet and device investigation, rules, versions, lifecycle, and upgrade impact.

Classification uses weighted lexical signals with explicit priorities and negative signals for ambiguous phrases. Confidence is a bounded classification score, not a probability calibrated against production traffic. Unknown but device-shaped questions fall back to `DeviceInvestigation`; other unknown questions fall back to `ConceptExplanation` at lower confidence.

## Entity Model

The extractor recognizes the 15 entity categories in `entity_catalog.json`. It currently extracts:

- Device identifiers such as `Laptop001` and `Device123`.
- Component-specific versions such as BIOS `2.1` and firmware `3.2`.
- Generic version lists.
- Rule and document IDs.
- Risk levels, recommendation types, violations, and root causes.
- Mentioned component categories even when no version is present.

Extraction retains original device casing and normalizes rule/document IDs to uppercase. Component keys use snake case in query plans.

## Routing Logic

- `Layer1`: Domain definitions and universal component knowledge.
- `Layer2`: Device and fleet inventory state.
- `Layer3`: Compatibility rules, constraints, dependencies, conflicts, lifecycle, and evidence.

Intent routes provide the baseline. A detected device always adds Layer 2. A rule, violation, or root-cause reference adds Layer 3. Layer order is always `Layer1`, `Layer2`, `Layer3`.

Examples:

| Question | Primary intent | Route |
|---|---|---|
| What is BIOS? | ConceptExplanation | Layer1 |
| Why is Laptop001 failing? | RootCauseAnalysis | Layer2 + Layer3 |
| Which firmware version is required? | VersionAnalysis | Layer3 |
| How does BIOS affect compliance? | ComplianceStatus | Layer1 + Layer3 when concept classification is also supported |
| Does BIOS 2.1 support Firmware 3.2? | CompatibilityInquiry | Layer3 |

## Operation

Run a query from the project root:

```powershell
python ReasoningLayer/query_understanding/query_understanding_service.py "Why is Laptop001 failing?"
```

Regenerate catalogs and corpora:

```powershell
python ReasoningLayer/query_understanding/build_query_understanding_assets.py
```

Execute tests and generate reports:

```powershell
python -m unittest ReasoningLayer.query_understanding.tests.test_query_understanding -v
python ReasoningLayer/query_understanding/validate_query_understanding.py
```

## Extension Strategy

1. Add an intent to `INTENT_SPECS`, its weighted signals, route, action, and at least ten patterns.
2. Add a new entity to `ENTITY_SPECS` and implement extraction rules before declaring it operational.
3. Prefer specific multi-word signals over broad words. Add negative signals where ordinary question phrasing creates false secondary intents.
4. Route only to layers that supply required evidence. Reasoning actions belong in `required_action`; they are not retrieval layers.
5. Add representative cases across the appropriate Layer 1, Layer 2, Layer 3, or hybrid partition.
6. Regenerate assets, run the full suite, and require every accuracy metric to remain above 90%.
7. Treat confidence below the consumer's acceptance threshold as a clarification or fallback-retrieval case rather than silently asserting certainty.

## Validation Scope

The checked corpus contains 250 cases: 50 Layer 1, 50 Layer 2, 50 Layer 3, and 100 hybrid. Validation measures exact primary intent, expected entity subset, exact ordered routing, and complete parsing. The generated metrics are a regression benchmark for this controlled corpus; production quality should also be monitored against independently labeled user traffic.
