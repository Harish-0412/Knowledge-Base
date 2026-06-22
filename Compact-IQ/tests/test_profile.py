from fastapi.testclient import TestClient

from app.db.models import Document, DocumentProfile, ExtractionJob
from app.db.session import SessionLocal
from app.main import app


client = TestClient(app)


def upload_file(filename: str, content: bytes, content_type: str) -> str:
    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def test_profile_txt_file():
    document_id = upload_file("release-notes.txt", b"Compatibility notes", "text/plain")

    response = client.post(f"/api/documents/{document_id}/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["profiles"] == [
        {
            "page_number": 1,
            "page_type": "text",
            "recommended_extractor": "text",
            "confidence": 0.95,
            "reason": "Plain text document",
            "signals_json": {},
        }
    ]


def test_profile_csv_file():
    document_id = upload_file("matrix.csv", b"product,version\nA,1", "text/csv")

    response = client.post(f"/api/documents/{document_id}/profile")

    assert response.status_code == 200
    profile = response.json()["profiles"][0]
    assert profile["page_type"] == "table"
    assert profile["recommended_extractor"] == "csv"
    assert profile["reason"] == "CSV compatibility matrix"


def test_profile_missing_document_returns_404():
    response = client.post("/api/documents/DOC-MISSING/profile")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def test_profile_creates_db_rows_and_job():
    document_id = upload_file("notes.md", b"# Compatibility", "text/markdown")

    response = client.post(f"/api/documents/{document_id}/profile")

    assert response.status_code == 200
    assert SessionLocal is not None
    with SessionLocal() as db:
        profiles = db.query(DocumentProfile).filter(DocumentProfile.document_id == document_id).all()
        jobs = db.query(ExtractionJob).filter(ExtractionJob.document_id == document_id).all()

    assert len(profiles) == 1
    assert profiles[0].recommended_extractor == "text"
    assert len(jobs) == 1
    assert jobs[0].job_type == "profile"
    assert jobs[0].status == "succeeded"


def test_profile_updates_document_status():
    document_id = upload_file("notes.txt", b"Compatibility", "text/plain")

    response = client.post(f"/api/documents/{document_id}/profile")

    assert response.status_code == 200
    assert SessionLocal is not None
    with SessionLocal() as db:
        document = db.get(Document, document_id)

    assert document is not None
    assert document.status == "profiled"


def test_repeated_profiling_replaces_previous_profile_cleanly():
    document_id = upload_file("notes.txt", b"Compatibility", "text/plain")

    first_response = client.post(f"/api/documents/{document_id}/profile")
    second_response = client.post(f"/api/documents/{document_id}/profile")
    get_response = client.get(f"/api/documents/{document_id}/profile")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert get_response.status_code == 200
    assert len(get_response.json()["profiles"]) == 1

    assert SessionLocal is not None
    with SessionLocal() as db:
        profiles = db.query(DocumentProfile).filter(DocumentProfile.document_id == document_id).all()
        jobs = db.query(ExtractionJob).filter(ExtractionJob.document_id == document_id).all()

    assert len(profiles) == 1
    assert len(jobs) == 2
    assert {job.status for job in jobs} == {"succeeded"}
