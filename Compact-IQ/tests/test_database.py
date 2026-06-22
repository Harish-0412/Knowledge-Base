from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_db_health_works():
    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database_url_configured": True,
    }
