from fastapi.testclient import TestClient

from app.db.models import RuleCandidate
from app.db.session import SessionLocal
from app.main import app
from app.schemas.llm_rule_extraction import LLMExtractionResponse
from app.core.errors import AppError
from app.services.rule_extraction_service import RuleExtractionService
from app.services.schema_validation_service import SchemaValidationService


client = TestClient(app)


def upload_file(filename: str, content: bytes, content_type: str) -> str:
    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def test_extract_rules_from_mock_txt_document():
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["rule_candidates_created"] == 1
    assert body["normalization_status"] == "normalized"
    assert body["warnings"] == []


def test_rule_candidates_are_stored_and_link_to_chunks():
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    client.post(f"/api/documents/{document_id}/extract-rules")

    assert SessionLocal is not None
    with SessionLocal() as db:
        candidates = db.query(RuleCandidate).filter(RuleCandidate.document_id == document_id).all()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_chunk_id is not None
    assert candidate.source_excerpt
    assert candidate.review_status == "pending_review"
    assert candidate.normalization_status in {"normalized", "needs_human_review"}
    assert candidate.raw_llm_output_json["rule_candidates"]


def test_get_rule_candidates_by_document_and_id():
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    client.post(f"/api/documents/{document_id}/extract-rules")

    list_response = client.get(f"/api/documents/{document_id}/rule-candidates")

    assert list_response.status_code == 200
    candidates = list_response.json()["rule_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["source_excerpt"]

    candidate_id = candidates[0]["candidate_id"]
    single_response = client.get(f"/api/rule-candidates/{candidate_id}")
    all_response = client.get("/api/rule-candidates")

    assert single_response.status_code == 200
    assert single_response.json()["candidate_id"] == candidate_id
    assert all_response.status_code == 200
    assert len(all_response.json()) == 1


def test_unextracted_document_auto_extracts_first():
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")
    chunks_response = client.get(f"/api/documents/{document_id}/chunks")

    assert response.status_code == 200
    assert chunks_response.status_code == 200
    assert len(chunks_response.json()["chunks"]) >= 1


def test_invalid_llm_json_is_handled_safely(monkeypatch):
    class BrokenLLMService:
        provider = "broken"

        def generate_json(self, prompt: str, *, timeout_seconds: int | None = None, **kwargs):
            return "```json\nnot valid json\n```"

    monkeypatch.setattr(
        "app.services.rule_extraction_service.LLMServiceFactory.create",
        lambda: BrokenLLMService(),
    )
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")

    assert response.status_code == 200
    body = response.json()
    assert body["rule_candidates_created"] == 0
    assert body["warnings"]

    assert SessionLocal is not None
    with SessionLocal() as db:
        candidates = db.query(RuleCandidate).filter(RuleCandidate.document_id == document_id).all()

    assert candidates == []


def test_normalize_rule_candidate_endpoints():
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )
    extract_response = client.post(f"/api/documents/{document_id}/extract-rules?normalize=false")
    assert extract_response.status_code == 200
    assert extract_response.json()["normalization_status"] == "pending"

    list_response = client.get(f"/api/documents/{document_id}/rule-candidates")
    candidate = list_response.json()["rule_candidates"][0]
    assert candidate["normalization_status"] == "pending_normalization"

    normalize_one_response = client.post(f"/api/rule-candidates/{candidate['candidate_id']}/normalize")
    assert normalize_one_response.status_code == 200
    assert normalize_one_response.json()["normalization_status"] in {"normalized", "needs_human_review"}

    normalize_document_response = client.post(f"/api/documents/{document_id}/normalize-rule-candidates")
    assert normalize_document_response.status_code == 200
    assert normalize_document_response.json()["rule_candidates"][0]["normalized_rule_json"]


def test_rule_extraction_errors_when_mock_llm_not_explicitly_allowed(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("ALLOW_MOCK_LLM_RULE_EXTRACTION", "false")
    get_settings.cache_clear()
    document_id = upload_file(
        "rules.txt",
        b"Windows Server 2012 requires BIOS 1.3.5 or later.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "llm_not_called_mock_mode"
    get_settings.cache_clear()


def test_llm_request_schema_excludes_code_assigned_fields():
    schema = LLMExtractionResponse.model_json_schema()
    candidate_props = schema["$defs"]["LLMRuleCandidate"]["properties"]
    condition_props = schema["$defs"]["LLMComponentValue"]["properties"]
    requirement_props = schema["$defs"]["LLMRequirementValue"]["properties"]

    for field in [
        "candidate_id",
        "source_document_id",
        "source_chunk_id",
        "source_page",
        "source_excerpt",
        "review_status",
        "created_at",
        "tags",
    ]:
        assert field not in candidate_props

    assert "condition_id" not in condition_props
    assert "requirement_id" not in requirement_props


def test_back_flashing_rule_is_stamped_and_validates_against_sot_model(monkeypatch):
    class BackFlashLLMService:
        provider = "fixture"

        def generate_json(self, prompt: str, *, timeout_seconds: int | None = None, **kwargs):
            return {
                "rule_candidates": [
                    {
                        "rule_type": "min_version_constraint",
                        "condition_logic": "AND",
                        "conditions": [
                            {
                                "component_type": "cpu",
                                "component_name": None,
                                "component_family": "Intel Xeon E5-2400 V2",
                                "vendor": "Intel",
                                "operator": "installed",
                                "value_raw": "Intel Xeon E5-2400 V2 family",
                                "version_raw": None,
                                "version_scheme": None,
                            }
                        ],
                        "requirements": [
                            {
                                "component_type": "bios",
                                "component_name": "System BIOS",
                                "component_family": None,
                                "vendor": None,
                                "operator": ">=",
                                "value_raw": None,
                                "version_raw": "2.0.21",
                                "version_scheme": "semantic",
                                "requirement_kind": "min_version",
                            }
                        ],
                        "exceptions": [],
                        "severity": "critical",
                        "confidence_score": 0.95,
                        "confidence_reason": "Explicit back-flashing constraint.",
                        "remediation_hint": "Do not back-flash below BIOS 2.0.21 with this CPU family installed.",
                    }
                ]
            }

    monkeypatch.setattr(
        "app.services.rule_extraction_service.LLMServiceFactory.create",
        lambda: BackFlashLLMService(),
    )
    document_id = upload_file(
        "backflash.txt",
        (
            b"Back-flashing to BIOS versions earlier than 2.0.21 is not allowed "
            b"if Intel Xeon E5-2400 V2 family processors are installed."
        ),
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")

    assert response.status_code == 200
    assert response.json()["rule_candidates_created"] == 1
    with SessionLocal() as db:
        candidate = db.query(RuleCandidate).filter(RuleCandidate.document_id == document_id).one()
        assert candidate.normalized_rule_json is not None
        valid, errors = SchemaValidationService().validate_normalized_candidate(candidate.normalized_rule_json)

    assert valid is True
    assert errors == []
    assert candidate.normalized_rule_json["conditions"][0]["condition_id"] == "COND-001"
    assert candidate.normalized_rule_json["requirements"][0]["requirement_id"] == "REQ-001"
    assert candidate.normalized_rule_json["review_status"] == "pending_review"


def test_fabricated_version_is_grounding_flagged(monkeypatch):
    class FabricatingLLMService:
        provider = "fixture"

        def generate_json(self, prompt: str, *, timeout_seconds: int | None = None, **kwargs):
            return {
                "rule_candidates": [
                    {
                        "rule_type": "min_version_constraint",
                        "condition_logic": "AND",
                        "conditions": [
                            {
                                "component_type": "os",
                                "component_name": "Windows Server 2012",
                                "component_family": None,
                                "vendor": None,
                                "operator": "installed",
                                "value_raw": "Windows Server 2012",
                                "version_raw": None,
                                "version_scheme": None,
                            }
                        ],
                        "requirements": [
                            {
                                "component_type": "bios",
                                "component_name": "System BIOS",
                                "component_family": None,
                                "vendor": None,
                                "operator": ">=",
                                "value_raw": None,
                                "version_raw": "9.9.9",
                                "version_scheme": "semantic",
                                "requirement_kind": "min_version",
                            }
                        ],
                        "exceptions": [],
                        "severity": "warning",
                        "confidence_score": 0.91,
                        "confidence_reason": "Fixture fabricated version.",
                        "remediation_hint": "Verify BIOS version.",
                    }
                ]
            }

    monkeypatch.setattr(
        "app.services.rule_extraction_service.LLMServiceFactory.create",
        lambda: FabricatingLLMService(),
    )
    document_id = upload_file(
        "fabricated.txt",
        b"Windows Server 2012 requires a supported BIOS version.",
        "text/plain",
    )

    response = client.post(f"/api/documents/{document_id}/extract-rules")

    assert response.status_code == 200
    with SessionLocal() as db:
        candidate = db.query(RuleCandidate).filter(RuleCandidate.document_id == document_id).one()

    assert candidate.review_status == "needs_clarification"
    assert candidate.confidence_score == 0.3
    assert "AUTO-FLAGGED" in candidate.confidence_reason
    assert candidate.normalized_rule_json["review_status"] == "needs_clarification"
    assert candidate.normalized_rule_json["tags"] == ["unverified_value"]


def test_guard_blocks_same_chunk_with_different_source_excerpts():
    with SessionLocal() as db:
        service = RuleExtractionService(db, llm_service=MockLLMForGuard())
        candidates = [
            RuleCandidate(
                document_id="DOC-ABCDEF123456",
                source_chunk_id=42,
                source_excerpt="System BIOS | 6.4.2",
                review_status="pending_review",
                normalization_status="pending_normalization",
                raw_llm_output_json={"rule_candidates": []},
            ),
            RuleCandidate(
                document_id="DOC-ABCDEF123456",
                source_chunk_id=42,
                source_excerpt="System Firmware | 8.2.1",
                review_status="pending_review",
                normalization_status="pending_normalization",
                raw_llm_output_json={"rule_candidates": []},
            ),
        ]

        try:
            service._guard_no_chunk_excerpt_mismatch(candidates)
            raised = None
        except AppError as exc:
            raised = exc

    assert raised is not None
    assert raised.code == "source_excerpt_chunk_mismatch"


class MockLLMForGuard:
    provider = "mock"

    def generate_json(self, prompt: str, **kwargs):
        return {"rule_candidates": []}
