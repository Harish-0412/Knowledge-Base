from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_llm_test_endpoint_works_in_mock_mode():
    response = client.post(
        "/api/debug/llm-test",
        json={
            "prompt": "Extract one compatibility rule from: Windows Server 2012 requires BIOS 1.3.5 or later."
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["model"] == "gemma4:31b"
    assert body["ok"] is True
    assert "rule_candidates" in body["result"]
