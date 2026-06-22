from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository

router = APIRouter(tags=["Frontend Compatibility"])


@router.get("/rules/candidates")
def list_rule_candidates_alias(db: Session = Depends(get_db)) -> list[dict]:
    candidates = RuleCandidateRepository(db).list_all()
    return [_candidate_payload(candidate) for candidate in candidates]


@router.get("/rules/candidates/{candidate_id}")
def get_rule_candidate_alias(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    candidate = RuleCandidateRepository(db).get_by_id(candidate_id)
    if candidate is None:
        return {}
    return _candidate_payload(candidate)


@router.post("/rules/candidates/{candidate_id}/approve")
def approve_rule_candidate_alias(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    return _set_review_status(candidate_id, "approved", db)


@router.post("/rules/candidates/{candidate_id}/reject")
def reject_rule_candidate_alias(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    return _set_review_status(candidate_id, "rejected", db)


@router.post("/rules/candidates/{candidate_id}/clarify")
def clarify_rule_candidate_alias(candidate_id: int, db: Session = Depends(get_db)) -> dict:
    return _set_review_status(candidate_id, "needs_clarification", db)


@router.get("/rules/approved")
def list_approved_rules(db: Session = Depends(get_db)) -> list[dict]:
    candidates = RuleCandidateRepository(db).list_all()
    return [_candidate_payload(candidate) for candidate in candidates if candidate.review_status == "approved"]


@router.post("/documents/{document_id}/process")
def process_document_alias(document_id: str) -> dict:
    return {
        "document_id": document_id,
        "message": "Use POST /api/documents/{document_id}/run-docintel-pipeline for full processing.",
        "is_compatibility_alias": True,
    }


@router.get("/pipeline/stages")
def pipeline_stages() -> list[dict]:
    return [
        {"id": "profile", "label": "Profile", "status": "available"},
        {"id": "extract", "label": "Extract", "status": "available"},
        {"id": "extract_rules", "label": "Extract Rules", "status": "available"},
        {"id": "approval", "label": "Approval", "status": "temporary_review_only"},
        {"id": "compliance", "label": "Compliance", "status": "pending_backend_integration"},
    ]


@router.post("/pipeline/run")
def pipeline_run_placeholder() -> dict:
    return {
        "status": "not_started",
        "message": "Select a document and call /api/documents/{document_id}/run-docintel-pipeline.",
        "is_temporary_frontend_compatibility_stub": True,
    }


@router.get("/pipeline/status")
def pipeline_status_placeholder() -> dict:
    return {"status": "idle", "is_temporary_frontend_compatibility_stub": True}


@router.get("/recent-activity")
def recent_activity(db: Session = Depends(get_db)) -> list[dict]:
    documents = DocumentRepository(db).list_documents()[:10]
    return [
        {
            "id": document.document_id,
            "type": "document",
            "title": document.filename,
            "status": document.status,
            "timestamp": document.uploaded_at.isoformat() if document.uploaded_at else None,
        }
        for document in documents
    ]


@router.get("/health/services")
def service_health_summary() -> dict:
    return {
        "backend": "ok",
        "document_intelligence": "ok",
        "approval": "temporary_review_only",
        "inventory": "pending_backend_integration",
        "compliance": "pending_backend_integration",
    }


@router.get("/audit-logs")
def audit_logs_placeholder() -> list[dict]:
    return []


@router.post("/database/connect")
def database_connect_placeholder() -> dict:
    return {
        "status": "accepted",
        "message": "Frontend database URL was received. Runtime database switching is pending backend integration.",
        "is_temporary_frontend_compatibility_stub": True,
    }


@router.post("/inventory/connect-db")
def inventory_connect_placeholder() -> dict:
    return {
        "status": "accepted",
        "message": "Inventory DB connection UI is connected to a placeholder endpoint.",
        "is_temporary_frontend_compatibility_stub": True,
    }


@router.get("/devices")
def devices_placeholder() -> list[dict]:
    return []


@router.get("/compliance/summary")
@router.get("/compliance/scans/latest")
@router.get("/compliance/scans/SCAN-000001")
def compliance_summary_placeholder() -> dict:
    return {
        "violations": 0,
        "compliant": 0,
        "status": "pending_backend_integration",
        "is_temporary_frontend_compatibility_stub": True,
    }


@router.get("/compliance/violations")
@router.get("/compliance/scans/latest/violations")
@router.get("/compliance/scans/SCAN-000001/violations")
def compliance_violations_placeholder() -> list[dict]:
    return []


@router.post("/compliance/scan")
def compliance_scan_placeholder() -> dict:
    return {
        "status": "not_started",
        "message": "Compliance scan engine is pending backend integration.",
        "is_temporary_frontend_compatibility_stub": True,
    }


@router.post("/assistant/query")
def assistant_query_placeholder(payload: dict | None = None) -> dict:
    prompt = (payload or {}).get("query") or (payload or {}).get("message") or ""
    return {
        "response": (
            "The document intelligence backend is connected. "
            "Assistant reasoning over approved rules, inventory, and compliance scans is pending backend integration."
        ),
        "query": prompt,
        "is_temporary_frontend_compatibility_stub": True,
    }


def _set_review_status(candidate_id: int, review_status: str, db: Session) -> dict:
    candidate = RuleCandidateRepository(db).get_by_id(candidate_id)
    if candidate is None:
        return {
            "candidate_id": candidate_id,
            "review_status": "not_found",
            "is_temporary_review_flow": True,
        }
    candidate.review_status = review_status
    db.commit()
    return {
        **_candidate_payload(candidate),
        "message": "Review status updated. Full approved-rule promotion is pending backend integration.",
        "is_temporary_review_flow": True,
    }


def _candidate_payload(candidate) -> dict:
    normalized = candidate.normalized_rule_json if isinstance(candidate.normalized_rule_json, dict) else {}
    return {
        "id": candidate.candidate_id,
        "candidate_id": candidate.candidate_id,
        "rule_id": candidate.rule_id,
        "rule_type": candidate.rule_type,
        "ruleType": candidate.rule_type,
        "severity": candidate.severity,
        "confidence": int((candidate.confidence_score or 0) * 100),
        "confidence_score": candidate.confidence_score,
        "review_status": candidate.review_status,
        "status": candidate.review_status,
        "normalization_status": candidate.normalization_status,
        "document_id": candidate.document_id,
        "document": candidate.document_id,
        "source_excerpt": candidate.source_excerpt,
        "normalized_rule_json": normalized,
        "subject": _first_value(normalized.get("conditions")),
        "predicate": candidate.rule_type or "rule",
        "object": _first_value(normalized.get("requirements")),
    }


def _first_value(items) -> str:
    if not items:
        return ""
    first = items[0] if isinstance(items, list) else items
    return str(first.get("component_name") or first.get("value_raw") or first.get("version_raw") or "")
