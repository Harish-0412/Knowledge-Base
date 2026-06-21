from ReasoningLayer.llm.connectors.ollama_connector import OllamaConnector


def test_ollama_running_and_model_reachable() -> None:
    health = OllamaConnector().health_check()
    assert health["reachable"], health["error"]
    assert health["model_reachable"], health["error"]


def test_ollama_generation() -> None:
    response = OllamaConnector().test_generation("What is BIOS?")
    assert response.strip()
