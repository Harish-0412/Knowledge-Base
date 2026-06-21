"""Evidence Aggregation Layer — Layer 4 Phase 3."""
from importlib import import_module as _imp
__all__ = [
    "EvidenceService",
    "EvidenceAggregator",
    "EvidenceCollector",
    "EvidenceRanker",
    "EvidenceGraphBuilder",
    "QdrantRetriever",
    "Neo4jRetriever",
]
def __getattr__(name):
    mod_map = {
        "EvidenceService":      ".evidence_service",
        "EvidenceAggregator":   ".evidence_aggregator",
        "EvidenceCollector":    ".evidence_collector",
        "EvidenceRanker":       ".evidence_ranker",
        "EvidenceGraphBuilder": ".evidence_graph_builder",
        "QdrantRetriever":      ".qdrant_retriever",
        "Neo4jRetriever":       ".neo4j_retriever",
    }
    if name in mod_map:
        mod = _imp(mod_map[name], package=__name__)
        return getattr(mod, name)
    raise AttributeError(name)
