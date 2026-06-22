from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorResponse
from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository
from app.schemas.export import RuleCandidateExportResponse

router = APIRouter(prefix="/export", tags=["Export"], responses={404: {"model": ErrorResponse}})


@router.get("/document/{document_id}/rule-candidates", response_model=RuleCandidateExportResponse)
def export_document_rule_candidates(document_id: str, db: Session = Depends(get_db)) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise AppError(
            code="document_not_found",
            message="Document was not found.",
            status_code=404,
            details={"document_id": document_id},
        )

    candidates = RuleCandidateRepository(db).list_by_document(document_id)
    normalized_candidates = [
        candidate.normalized_rule_json
        for candidate in candidates
        if candidate.normalized_rule_json and candidate.review_status == "pending_review"
    ]
    return {
        "document_id": document_id,
        "export_type": "normalized_rule_candidates",
        "rule_candidates": normalized_candidates,
    }
