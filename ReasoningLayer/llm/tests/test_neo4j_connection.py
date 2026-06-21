from ReasoningLayer.llm.connectors.neo4j_connector import Neo4jConnector


def test_neo4j_reachable_and_query_executes() -> None:
    connector = Neo4jConnector()
    try:
        health = connector.health_check()
        assert health["reachable"], health["error"]
        assert health["test_query"] == {"result": 1}
    finally:
        connector.close()
