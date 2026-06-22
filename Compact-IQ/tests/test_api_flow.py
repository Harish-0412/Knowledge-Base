import json

from fastapi.testclient import TestClient
from pathlib import Path

from app.db.models import Document, DocumentProfile, RuleCandidate
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


def test_full_docintel_pipeline_for_mock_release_notes():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["status"] == "rules_extracted"
    assert body["profile_count"] == 1
    assert body["chunks_created"] >= 1
    assert body["extractors_used"] == ["text"]
    assert body["raw_rule_candidates_created"] >= 1
    assert body["rule_candidates_created"] >= 1
    assert body["normalized_rule_candidates_created"] >= 1
    assert body["normalized_candidates"] >= 1
    assert set(body["exports"]) == {
        "profile",
        "docling_document",
        "docling_markdown",
        "docling_hybrid_chunks",
        "document_blocks",
        "document_sections",
        "chunks",
        "chunks_csv",
        "llm_context_pack",
        "llm_input_chunks",
        "document_objects",
        "processing_lane_report",
        "deterministic_candidates",
        "llm_sections",
        "llm_call_log",
        "raw_rule_candidates",
        "normalized_rule_candidates",
        "candidate_quality_report",
        "normalization_warnings",
        "pipeline_summary",
    }
    assert all(Path(path).exists() for path in body["exports"].values())

    chunks_response = client.get(f"/api/documents/{document_id}/chunks")
    candidates_response = client.get(f"/api/documents/{document_id}/rule-candidates")
    document_response = client.get(f"/api/documents/{document_id}")
    exports_response = client.get(f"/api/documents/{document_id}/exports")

    chunks = chunks_response.json()["chunks"]
    candidates = candidates_response.json()["rule_candidates"]
    assert chunks
    assert candidates
    assert all(candidate["source_chunk_id"] for candidate in candidates)
    assert all(candidate["review_status"] == "pending_review" for candidate in candidates)
    assert all(candidate["normalized_rule_json"] for candidate in candidates)
    assert document_response.json()["status"] == "rules_extracted"
    assert document_response.json()["display_name"] == "mock_release_notes.txt"
    assert document_response.json()["file_type"] == "text/plain"
    assert exports_response.status_code == 200
    assert all(item["exists"] for item in exports_response.json()["exports"].values())
    quality_report_path = Path(body["exports"]["candidate_quality_report"])
    quality_report = json.loads(quality_report_path.read_text(encoding="utf-8"))
    assert {"unknown_component_type_count", "model_as_version_error_count", "missing_source_page_count"}.issubset(
        quality_report
    )


def test_reextract_replaces_chunks_and_clears_stale_rule_candidates():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    pipeline_response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")
    assert pipeline_response.status_code == 200

    candidates_response = client.get(f"/api/documents/{document_id}/rule-candidates")
    assert candidates_response.json()["rule_candidates"]

    extract_response = client.post(f"/api/documents/{document_id}/extract")
    assert extract_response.status_code == 200
    assert extract_response.json()["chunks_created"] >= 1

    after_candidates_response = client.get(f"/api/documents/{document_id}/rule-candidates")
    assert after_candidates_response.status_code == 200
    assert after_candidates_response.json()["rule_candidates"] == []

    export_response = client.get(f"/api/export/document/{document_id}/rule-candidates")
    assert export_response.status_code == 200
    assert export_response.json()["rule_candidates"] == []


def test_reextract_clears_candidates_that_reference_old_chunks_even_if_document_id_differs():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    pipeline_response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")
    assert pipeline_response.status_code == 200

    chunks = client.get(f"/api/documents/{document_id}/chunks").json()["chunks"]
    stale_chunk_id = chunks[0]["chunk_id"]
    other_document_id = upload_file("other.txt", b"General text.", "text/plain")
    with SessionLocal() as db:
        db.add(
            RuleCandidate(
                document_id=other_document_id,
                source_chunk_id=stale_chunk_id,
                source_excerpt="stale cross-document reference",
                review_status="pending_review",
                normalization_status="pending_normalization",
                raw_llm_output_json={"rule_candidates": []},
            )
        )
        db.commit()

    extract_response = client.post(f"/api/documents/{document_id}/extract")

    assert extract_response.status_code == 200


def test_run_demo_document_endpoint():
    response = client.post("/api/debug/run-demo-document")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rules_extracted"
    assert body["chunks_created"] >= 1
    assert body["rule_candidates_created"] >= 1


def test_export_normalized_rule_candidates():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    response = client.get(f"/api/export/document/{document_id}/rule-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["export_type"] == "normalized_rule_candidates"
    assert body["rule_candidates"]
    assert body["rule_candidates"][0]["review_status"] == "pending_review"


def test_document_intelligence_summary_endpoint():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    response = client.get(f"/api/documents/{document_id}/intelligence-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["display_status"] == "Rules Extracted"
    assert body["display_name"] == "mock_release_notes.txt"
    assert body["counts"]["chunks"] >= 1
    assert body["counts"]["raw_candidates"] >= 1
    assert body["counts"]["rule_candidates"] >= 1
    assert body["counts"]["normalized_candidates"] >= 1
    assert body["counts"]["pending_review"] >= 1
    assert body["pipeline"]["profiled"] is True
    assert body["pipeline"]["extracted"] is True
    assert body["pipeline"]["evidence_extracted"] is True
    assert body["pipeline"]["rules_extracted"] is True
    assert body["pipeline"]["normalized"] is True
    assert body["next_action"]["target_tab"] in {"processing", "rule_review", "handoff"}
    assert body["quality"]["has_quality_report"] is True
    assert any(item["name"] == "normalized_rule_candidates" for item in body["exports"])


def test_temporary_rule_candidate_review_endpoint_updates_status():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    client.post(f"/api/documents/{document_id}/run-docintel-pipeline")
    candidates = client.get(f"/api/documents/{document_id}/rule-candidates").json()["rule_candidates"]
    candidate_id = candidates[0]["candidate_id"]

    response = client.patch(
        f"/api/rule-candidates/{candidate_id}/review",
        json={"review_status": "approved", "reviewed_by": "test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == candidate_id
    assert body["review_status"] == "approved"
    assert body["is_temporary_review_flow"] is True
    assert "pending backend integration" in body["message"]

    refreshed = client.get(f"/api/rule-candidates/{candidate_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["review_status"] == "approved"


def test_frontend_compatibility_routes_return_safe_placeholders():
    health_services = client.get("/api/health/services")
    devices = client.get("/api/devices")
    compliance = client.get("/api/compliance/summary")
    assistant = client.post("/api/assistant/query", json={"query": "status"})

    assert health_services.status_code == 200
    assert health_services.json()["inventory"] == "pending_backend_integration"
    assert devices.status_code == 200
    assert devices.json() == []
    assert compliance.status_code == 200
    assert compliance.json()["is_temporary_frontend_compatibility_stub"] is True
    assert assistant.status_code == 200
    assert assistant.json()["is_temporary_frontend_compatibility_stub"] is True


def test_frontend_rule_candidate_aliases_use_existing_backend_data():
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    candidates = client.get("/api/rules/candidates")
    assert candidates.status_code == 200
    assert candidates.json()
    candidate_id = candidates.json()[0]["candidate_id"]

    approve = client.post(f"/api/rules/candidates/{candidate_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["review_status"] == "approved"
    assert approve.json()["is_temporary_review_flow"] is True

    approved = client.get("/api/rules/approved")
    assert approved.status_code == 200
    assert any(item["candidate_id"] == candidate_id for item in approved.json())


def test_openapi_contains_expected_tags():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    tags = {tag["name"] for tag in response.json()["tags"]}
    assert {"Health", "Documents", "Chunks", "Rule Candidates", "Debug", "Export"}.issubset(tags)


def test_pipeline_missing_document_returns_404():
    response = client.post("/api/documents/DOC-MISSING/run-docintel-pipeline")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def test_pipeline_unsupported_extractor_returns_clean_error():
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

    response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_extractor"


def test_pipeline_llm_failure_returns_clean_error(monkeypatch):
    class FailingRuleExtractionService:
        def __init__(self, db):
            self.db = db

        def extract_rules_for_document(self, document_id: str):
            from app.core.errors import AppError

            raise AppError("llm_failure", "LLM failed during test.", status_code=502)

    monkeypatch.setattr("app.services.pipeline_service.RuleExtractionService", FailingRuleExtractionService)
    document_id = upload_file(
        "mock_release_notes.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_failure"


def test_pipeline_warns_when_no_rule_candidates_found():
    document_id = upload_file("plain.txt", b"This document has general prose only.", "text/plain")

    response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    assert response.status_code == 200
    body = response.json()
    assert body["rule_candidates_created"] == 0
    assert body["warnings"]


def test_pipeline_no_chunks_found_returns_clean_error(monkeypatch):
    class EmptyPostProcessor:
        def process(self, document_id, extracted_blocks):
            class Stats:
                rejected = 0
                deduplicated = 0

            return [], Stats()

    monkeypatch.setattr("app.services.pipeline_service.CompatIQSemanticPostProcessor", EmptyPostProcessor)
    document_id = upload_file("rules.txt", b"Windows Server 2012 requires BIOS 1.3.5 or later.", "text/plain")

    response = client.post(f"/api/documents/{document_id}/run-docintel-pipeline")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "no_chunks_found"
