from ReasoningLayer.llm.connectors.qdrant_connector import QdrantConnector


def test_qdrant_reachable() -> None:
    health = QdrantConnector().health_check()
    assert health["reachable"], health["error"]


def test_required_collections_exist() -> None:
    health = QdrantConnector().health_check()
    assert not health["missing_collections"], health
