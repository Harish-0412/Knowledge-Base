from fastapi.testclient import TestClient

from app.db.models import Document, DocumentChunk, DocumentProfile, ExtractionJob
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


def test_extract_txt_document_and_create_chunks():
    content = b"""# Release Notes

Version 1.0
- Supports Product A
- Requires Product B 2.0

Version 1.1
- Adds Product C compatibility
"""
    document_id = upload_file("release-notes.txt", content, "text/plain")

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["status"] == "extracted"
    assert body["chunks_created"] >= 2
    assert body["methods_used"] == ["text"]
    assert body["warnings"] == []

    assert SessionLocal is not None
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()

    assert document is not None
    assert document.status == "extracted"
    assert len(chunks) == body["chunks_created"]


def test_extract_csv_document_and_create_table_chunks():
    document_id = upload_file(
        "matrix.csv",
        b"product,version,status\nA,1,supported\nB,2,unsupported\n",
        "text/csv",
    )

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 200
    body = response.json()
    assert body["chunks_created"] == 2
    assert body["methods_used"] == ["csv"]

    chunks_response = client.get(f"/api/documents/{document_id}/chunks")
    chunks = chunks_response.json()["chunks"]
    assert {chunk["chunk_type"] for chunk in chunks} == {"component_table_row"}
    assert all(chunk["metadata_json"]["headers"] == ["product", "version", "status"] for chunk in chunks)


def test_extraction_auto_runs_profile_if_missing():
    document_id = upload_file("notes.txt", b"Compatibility paragraph.", "text/plain")

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 200
    assert SessionLocal is not None
    with SessionLocal() as db:
        profiles = db.query(DocumentProfile).filter(DocumentProfile.document_id == document_id).all()
        jobs = db.query(ExtractionJob).filter(ExtractionJob.document_id == document_id).all()

    assert len(profiles) == 1
    assert {job.job_type for job in jobs} == {"profile", "extract"}
    assert {job.status for job in jobs} == {"succeeded"}


def test_chunks_have_source_excerpt_and_page_number():
    document_id = upload_file("notes.txt", b"Compatibility paragraph.", "text/plain")

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 200
    chunks_response = client.get(f"/api/documents/{document_id}/chunks")
    chunks = chunks_response.json()["chunks"]
    assert chunks
    assert all(chunk["source_excerpt"] for chunk in chunks)
    assert all(chunk["page_number"] == 1 for chunk in chunks)


def test_get_chunks_by_document_and_single_chunk():
    document_id = upload_file("notes.txt", b"Compatibility paragraph.", "text/plain")
    client.post(f"/api/documents/{document_id}/extract")

    list_response = client.get(f"/api/documents/{document_id}/chunks")

    assert list_response.status_code == 200
    chunks = list_response.json()["chunks"]
    assert len(chunks) == 1

    chunk_id = chunks[0]["chunk_id"]
    single_response = client.get(f"/api/chunks/{chunk_id}")

    assert single_response.status_code == 200
    assert single_response.json()["chunk_id"] == chunk_id
    assert single_response.json()["document_id"] == document_id


def test_unsupported_extractor_returns_clean_error():
    document_id = upload_file(
        "sample.docx",
        b"placeholder docx bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert SessionLocal is not None
    with SessionLocal() as db:
        profile = DocumentProfile(
            document_id=document_id,
            page_number=1,
            page_type="document",
            recommended_extractor="unsupported_docx_placeholder",
            confidence=0.3,
            reason="Forced unsupported extractor for test.",
            signals_json={},
        )
        db.add(profile)
        db.commit()

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_extractor"

    with SessionLocal() as db:
        extract_jobs = (
            db.query(ExtractionJob)
            .filter(ExtractionJob.document_id == document_id, ExtractionJob.job_type == "extract")
            .all()
        )

    assert len(extract_jobs) == 1
    assert extract_jobs[0].status == "failed"
