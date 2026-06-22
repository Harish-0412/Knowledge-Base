from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_upload_txt_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("release-notes.txt", b"Compatibility notes for version 1.0", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"].startswith("DOC-")
    assert body["filename"].endswith(".txt")
    assert body["original_filename"] == "release-notes.txt"
    assert body["source_type"] == "text"
    assert body["status"] == "uploaded"
    assert body["file_size_bytes"] == len(b"Compatibility notes for version 1.0")


def test_reject_unsupported_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_reject_too_large_file(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()

    try:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("large.txt", b"x" * ((1024 * 1024) + 1), "text/plain")},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_get_uploaded_document():
    upload_response = client.post(
        "/api/documents/upload",
        files={"file": ("matrix.csv", b"product,version\nA,1", "text/csv")},
    )
    document_id = upload_response.json()["document_id"]

    response = client.get(f"/api/documents/{document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["source_type"] == "csv"
    assert body["status"] == "uploaded"


def test_list_documents():
    client.post(
        "/api/documents/upload",
        files={"file": ("one.md", b"# One", "text/markdown")},
    )
    client.post(
        "/api/documents/upload",
        files={"file": ("two.pdf", b"%PDF-1.4", "application/pdf")},
    )

    response = client.get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {document["source_type"] for document in body} == {"markdown", "pdf"}
