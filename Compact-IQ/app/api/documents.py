import json
import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorResponse
from app.db.models import Document
from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_profile_repository import DocumentProfileRepository
from app.repositories.extraction_job_repository import ExtractionJobRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository
from app.schemas.document_chunk import DocumentChunkListResponse, DocumentExtractResponse
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.schemas.document_profile import DocumentProfileResponse
from app.schemas.exports import DocumentExportsResponse
from app.schemas.pipeline import DocIntelPipelineResponse
from app.schemas.rule_candidate import RuleCandidateListResponse, RuleExtractionResponse
from app.services.compatiq_semantic_post_processor import CompatIQSemanticPostProcessor
from app.services.candidate_quality_service import CandidateQualityService
from app.services.document_storage_service import DocumentStorageService
from app.services.extraction_router_service import ExtractionRouterService
from app.services.profiler_service import ProfilerService
from app.services.rule_extraction_service import RuleExtractionService
from app.services.normalization_service import NormalizationService
from app.services.processing_lane_service import CandidateQualityGate, ProcessingLaneRuleExtractionService
from app.services.pipeline_service import DocIntelPipelineService
from app.services.local_export_service import LocalExportService
from app.services.llm_context_pack_builder import LLMContextPackBuilder
from app.core.config import get_settings

ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"], responses=ERROR_RESPONSES)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Document:
    stored = await DocumentStorageService().save_upload(file)
    document = Document(
        document_id=stored.document_id,
        filename=stored.filename,
        original_filename=stored.original_filename,
        file_path=stored.file_path,
        content_type=stored.content_type,
        source_type=stored.source_type,
        file_size_bytes=stored.file_size_bytes,
        status="uploaded",
        metadata_json={},
    )

    saved_document = DocumentRepository(db).create_document(document)
    logger.info("document uploaded", extra={"document_id": saved_document.document_id})
    return saved_document


@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return DocumentRepository(db).list_documents()


def _run_profile(document: Document, db: Session) -> list:
    logger.info("profiling started", extra={"document_id": document.document_id})
    job_repository = ExtractionJobRepository(db)
    job = job_repository.create_running_job(document_id=document.document_id, job_type="profile")
    try:
        profiles = ProfilerService().profile_document(document)
        saved_profiles = DocumentProfileRepository(db).replace_profiles(document.document_id, profiles)
        LocalExportService().write(
            document.document_id,
            "profile",
            {"document_id": document.document_id, "profiles": saved_profiles},
        )
        DocumentRepository(db).update_document_status(document.document_id, "profiled")
        job_repository.mark_succeeded(job)
        logger.info("profiling finished", extra={"document_id": document.document_id, "profile_count": len(saved_profiles)})
        return saved_profiles
    except Exception as exc:
        db.rollback()
        job_repository.mark_failed(job, str(exc))
        raise


@router.post("/{document_id}/profile", response_model=DocumentProfileResponse)
def profile_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document_repository = DocumentRepository(db)
    document = document_repository.get_document(document_id)
    if document is None:
        raise _document_not_found(document_id)

    saved_profiles = _run_profile(document, db)

    return {
        "document_id": document_id,
        "profiles": saved_profiles,
    }


@router.get("/{document_id}/profile", response_model=DocumentProfileResponse)
def get_document_profile(document_id: str, db: Session = Depends(get_db)) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise _document_not_found(document_id)

    profiles = DocumentProfileRepository(db).list_profiles(document_id)
    return {
        "document_id": document_id,
        "profiles": profiles,
    }


@router.post("/{document_id}/extract", response_model=DocumentExtractResponse)
def extract_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    return _run_extract(document_id, db)


def _run_extract(document_id: str, db: Session) -> dict:
    logger.info("extraction started", extra={"document_id": document_id})
    document_repository = DocumentRepository(db)
    document = document_repository.get_document(document_id)
    if document is None:
        raise _document_not_found(document_id)

    profile_repository = DocumentProfileRepository(db)
    profiles = profile_repository.list_profiles(document_id)
    if not profiles:
        profiles = _run_profile(document, db)

    job_repository = ExtractionJobRepository(db)
    job = job_repository.create_running_job(document_id=document_id, job_type="extract")

    try:
        extracted_blocks, warnings = ExtractionRouterService().extract(document, profiles)
        chunks, chunking_service = CompatIQSemanticPostProcessor().process(document_id, extracted_blocks)
        saved_chunks = ChunkRepository(db).replace_chunks(document_id, chunks)
        export_service = LocalExportService()
        export_service.write_chunks(document_id, saved_chunks)
        export_service.write(document_id, "llm_context_pack", LLMContextPackBuilder().build(document_id, saved_chunks))
        export_service.write(document_id, "raw_rule_candidates", {"document_id": document_id, "rule_candidates": []})
        export_service.write(
            document_id,
            "normalized_rule_candidates",
            {"document_id": document_id, "rule_candidates": []},
        )
        export_service.write(document_id, "candidate_quality_report", CandidateQualityService().build_report([]))
        export_service.write(document_id, "normalization_warnings", {"document_id": document_id, "warnings": []})
        document_repository.update_document_status(document_id, "extracted")
        job_repository.mark_succeeded(job)
    except Exception as exc:
        db.rollback()
        job_repository.mark_failed(job, str(exc))
        raise

    methods_used = sorted({chunk.extraction_method for chunk in saved_chunks})
    likelihood_summary = _rule_likelihood_summary(saved_chunks)
    semantic_zone_summary = _field_summary(saved_chunks, "semantic_zone")
    llm_usage_summary = _field_summary(saved_chunks, "llm_usage")
    parser_used = sorted({chunk.source_parser or chunk.extraction_method for chunk in saved_chunks})
    source_chunker = sorted({chunk.source_chunker or "compatiq_semantic_chunker" for chunk in saved_chunks})
    logger.info("extraction finished", extra={"document_id": document_id, "chunks_created": len(saved_chunks)})
    return {
        "document_id": document_id,
        "status": "extracted",
        "preferred_parser": get_settings().preferred_parser,
        "parser_used": parser_used[0] if len(parser_used) == 1 else ",".join(parser_used),
        "source_chunker": source_chunker[0] if len(source_chunker) == 1 else ",".join(source_chunker),
        "chunks_created": len(saved_chunks),
        "chunks_rejected": chunking_service.stats.rejected,
        "chunks_deduplicated": chunking_service.stats.deduplicated,
        "methods_used": methods_used,
        "semantic_zone_summary": semantic_zone_summary,
        "llm_usage_summary": llm_usage_summary,
        "rule_likelihood_summary": likelihood_summary,
        "llm_input_chunk_count": sum(1 for chunk in saved_chunks if chunk.send_to_llm),
        "llm_rule_extraction_chunk_count": sum(1 for chunk in saved_chunks if chunk.llm_usage == "rule_extraction"),
        "warnings": warnings,
    }


@router.get("/{document_id}/chunks", response_model=DocumentChunkListResponse)
def get_document_chunks(
    document_id: str,
    send_to_llm: bool | None = Query(default=None),
    rule_likelihood: str | None = Query(default=None),
    chunk_type: str | None = Query(default=None),
    llm_usage: str | None = Query(default=None),
    semantic_zone: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise _document_not_found(document_id)

    chunks = ChunkRepository(db).list_chunks_for_document(
        document_id,
        send_to_llm=send_to_llm,
        rule_likelihood=rule_likelihood,
        chunk_type=chunk_type,
        llm_usage=llm_usage,
        semantic_zone=semantic_zone,
    )
    return {
        "document_id": document_id,
        "chunks": chunks,
    }


@router.get("/{document_id}/exports", response_model=DocumentExportsResponse)
def get_document_exports(document_id: str, db: Session = Depends(get_db)) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise _document_not_found(document_id)

    return {
        "document_id": document_id,
        "exports": LocalExportService().export_status(document_id),
    }


@router.get("/{document_id}/intelligence-summary")
def get_document_intelligence_summary(document_id: str, db: Session = Depends(get_db)) -> dict:
    document_repository = DocumentRepository(db)
    document = document_repository.get_document(document_id)
    if document is None:
        raise _document_not_found(document_id)

    chunks = ChunkRepository(db).list_chunks_for_document(document_id)
    candidates = RuleCandidateRepository(db).list_by_document(document_id)
    profiles = DocumentProfileRepository(db).list_profiles(document_id)
    export_service = LocalExportService()
    exports = export_service.export_status(document_id)
    quality_report = _read_quality_report(export_service, document_id)
    quality_warnings = quality_report.get("warnings", []) if quality_report else []
    normalized_candidates = [candidate for candidate in candidates if candidate.normalized_rule_json]

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "original_filename": document.original_filename,
        "display_name": document.display_name,
        "file_type": _document_file_type(document),
        "source_type": document.source_type,
        "status": document.status,
        "display_status": _display_document_status(document.status),
        "uploaded_at": document.uploaded_at,
        "updated_at": document.updated_at,
        "parser": _primary_parser(chunks, profiles),
        "counts": {
            "chunks": len(chunks),
            "raw_candidates": len(candidates),
            "rule_candidates": len(candidates),
            "normalized_candidates": len(normalized_candidates),
            "pending_review": _review_count(candidates, "pending_review"),
            "approved_for_next_stage": _review_count(candidates, "approved"),
            "needs_clarification": _review_count(candidates, "needs_clarification"),
            "rejected": _review_count(candidates, "rejected"),
            "quality_warnings": len(quality_warnings),
        },
        "pipeline": {
            "profiled": bool(profiles) or document.status in {"profiled", "extracted", "rules_extracted", "normalized", "ready_for_review"},
            "extracted": bool(chunks) or document.status in {"extracted", "rules_extracted", "normalized", "ready_for_review"},
            "evidence_extracted": bool(chunks) or document.status in {"extracted", "rules_extracted", "normalized", "ready_for_review"},
            "rules_extracted": bool(candidates) or document.status in {"rules_extracted", "normalized", "ready_for_review"},
            "normalized": bool(normalized_candidates),
            "review_started": any(candidate.review_status != "pending_review" for candidate in candidates),
            "last_pipeline_step": _last_pipeline_step(document.status, chunks, candidates, normalized_candidates),
        },
        "next_action": _next_document_action(profiles, chunks, candidates, normalized_candidates),
        "quality": {
            "has_quality_report": quality_report is not None,
            "critical_warning_count": len(quality_warnings),
            "warnings": quality_warnings,
            "report": quality_report,
        },
        "exports": [
            {"name": name, **status}
            for name, status in exports.items()
        ],
    }


@router.post("/{document_id}/run-docintel-pipeline", response_model=DocIntelPipelineResponse)
def run_docintel_pipeline(document_id: str, db: Session = Depends(get_db)) -> dict:
    return DocIntelPipelineService(db).run(document_id)


@router.post("/{document_id}/extract-rules", response_model=RuleExtractionResponse)
def extract_rules(document_id: str, normalize: bool = True, db: Session = Depends(get_db)) -> dict:
    logger.info("rule extraction started", extra={"document_id": document_id, "normalize": normalize})
    document_repository = DocumentRepository(db)
    document = document_repository.get_document(document_id)
    if document is None:
        raise _document_not_found(document_id)

    if not ChunkRepository(db).list_chunks_for_document(document_id):
        _run_extract(document_id, db)

    job_repository = ExtractionJobRepository(db)
    job = job_repository.create_running_job(document_id=document_id, job_type="extract_rules")
    try:
        extraction_debug: dict = {}
        if get_settings().extraction_pipeline_mode == "processing_lanes":
            candidates, warnings, extraction_debug = ProcessingLaneRuleExtractionService(db).extract_rules_for_document(document_id)
        else:
            candidates, warnings = RuleExtractionService(db).extract_rules_for_document(document_id)
        normalized_statuses: set[str] = set()
        if normalize:
            normalization_service = NormalizationService()
            for candidate in candidates:
                normalization_service.normalize_candidate(candidate)
                CandidateQualityGate().apply(candidate, strict=get_settings().quality_gate_strict)
                RuleCandidateRepository(db).save(candidate)
                logger.info(
                    "normalization finished",
                    extra={
                        "document_id": document_id,
                        "candidate_id": candidate.candidate_id,
                        "normalization_status": candidate.normalization_status,
                    },
                )
            normalized_statuses = {candidate.normalization_status for candidate in candidates}
        LocalExportService().write(
            document_id,
            "raw_rule_candidates",
            {
                "document_id": document_id,
                "rule_candidates": [
                    {
                        "candidate_id": candidate.candidate_id,
                        "document_id": candidate.document_id,
                        "source_chunk_id": candidate.source_chunk_id,
                        "source_excerpt": candidate.source_excerpt,
                        "raw_llm_output_json": candidate.raw_llm_output_json,
                        "review_status": candidate.review_status,
                        "normalization_status": candidate.normalization_status,
                    }
                    for candidate in candidates
                ],
            },
        )
        LocalExportService().write(
            document_id,
            "normalized_rule_candidates",
            {
                "document_id": document_id,
                "rule_candidates": [
                    candidate.normalized_rule_json
                    for candidate in candidates
                    if candidate.normalized_rule_json
                ],
            },
        )
        quality_service = CandidateQualityService()
        quality_report = quality_service.build_report(candidates, warnings)
        LocalExportService().write(document_id, "candidate_quality_report", quality_report)
        LocalExportService().write(
            document_id,
            "normalization_warnings",
            {"document_id": document_id, "warnings": quality_report["warnings"]},
        )
        document_repository.update_document_status(document_id, "rules_extracted")
        job_repository.mark_succeeded(job)
    except Exception as exc:
        db.rollback()
        job_repository.mark_failed(job, str(exc))
        raise

    logger.info("rule extraction finished", extra={"document_id": document_id, "candidate_count": len(candidates)})
    summary = {
        "document_id": document_id,
        "rule_candidates_created": len(candidates),
        "normalization_status": (
            "normalized"
            if normalize and normalized_statuses == {"normalized"}
            else "needs_human_review"
            if normalize and "needs_human_review" in normalized_statuses
            else "pending"
        ),
        "candidate_quality": quality_service.summary_metrics(quality_report),
        "pipeline_mode": extraction_debug.get("pipeline_mode", get_settings().extraction_pipeline_mode),
        "total_objects": extraction_debug.get("total_objects", 0),
        "processing_lane_summary": extraction_debug.get("processing_lane_summary", {}),
        "llm_call_count": extraction_debug.get("llm_call_count", 0),
        "deterministic_candidate_count": extraction_debug.get("deterministic_candidate_count", 0),
        "llm_candidate_count": extraction_debug.get("llm_candidate_count", len(candidates)),
        "raw_rule_candidates_created": len(candidates),
        "normalized_rule_candidates_created": len([candidate for candidate in candidates if candidate.normalized_rule_json]),
        "quality_warning_count": len(quality_report.get("warnings", [])),
        "pipeline_stage": "rules_extracted",
        "exports": LocalExportService().export_status(document_id),
        "warnings": warnings,
    }
    return summary


@router.post("/{document_id}/normalize-rule-candidates", response_model=RuleCandidateListResponse)
def normalize_document_rule_candidates(document_id: str, db: Session = Depends(get_db)) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise _document_not_found(document_id)

    repository = RuleCandidateRepository(db)
    candidates = repository.list_by_document(document_id)
    normalization_service = NormalizationService()
    saved_candidates = []
    for candidate in candidates:
        normalization_service.normalize_candidate(candidate)
        saved_candidates.append(repository.save(candidate))
        logger.info(
            "normalization finished",
            extra={
                "document_id": document_id,
                "candidate_id": candidate.candidate_id,
                "normalization_status": candidate.normalization_status,
            },
        )

    return {
        "document_id": document_id,
        "rule_candidates": saved_candidates,
    }


@router.get("/{document_id}/rule-candidates")
def get_document_rule_candidates(document_id: str, db: Session = Depends(get_db)) -> dict:
    if DocumentRepository(db).get_document(document_id) is None:
        raise _document_not_found(document_id)

    candidates = RuleCandidateRepository(db).list_by_document(document_id)

    # Batch-fetch source chunks to enrich candidates with document location
    chunk_ids = {c.source_chunk_id for c in candidates if c.source_chunk_id}
    chunks_by_id = {
        chunk.chunk_id: chunk
        for chunk in ChunkRepository(db).get_by_ids(chunk_ids)
    }

    enriched = []
    for candidate in candidates:
        chunk = chunks_by_id.get(candidate.source_chunk_id)
        entry = {
            "candidate_id": candidate.candidate_id,
            "document_id": candidate.document_id,
            "source_chunk_id": candidate.source_chunk_id,
            "rule_id": candidate.rule_id,
            "rule_type": candidate.rule_type,
            "condition_logic": candidate.condition_logic,
            "conditions_json": candidate.conditions_json,
            "requirement_json": candidate.requirement_json,
            "severity": candidate.severity,
            "confidence_score": candidate.confidence_score,
            "confidence_reason": candidate.confidence_reason,
            "explanation": candidate.explanation,
            "source_excerpt": candidate.source_excerpt,
            "review_status": candidate.review_status,
            "normalization_status": candidate.normalization_status,
            "raw_llm_output_json": candidate.raw_llm_output_json,
            "normalized_rule_json": candidate.normalized_rule_json,
            "validation_errors_json": candidate.validation_errors_json,
            "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
            # Enriched chunk location fields
            "source_page": chunk.page_number if chunk else None,
            "source_section": chunk.section_title if chunk else None,
            "source_section_path": chunk.section_path_json if chunk else None,
            "source_chunk_index": chunk.chunk_index if chunk else None,
            "source_chunk_type": chunk.chunk_type if chunk else None,
            "source_semantic_zone": chunk.semantic_zone if chunk else None,
        }
        enriched.append(entry)

    return {
        "document_id": document_id,
        "rule_candidates": enriched,
    }


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    document = DocumentRepository(db).get_document(document_id)
    if document is None:
        raise _document_not_found(document_id)
    return document


def _document_not_found(document_id: str) -> AppError:
    return AppError(
        code="document_not_found",
        message="Document was not found.",
        status_code=404,
        details={"document_id": document_id},
    )


def _rule_likelihood_summary(chunks: list) -> dict[str, int]:
    summary = {"high": 0, "medium": 0, "low": 0}
    for chunk in chunks:
        summary[chunk.rule_likelihood] = summary.get(chunk.rule_likelihood, 0) + 1
    return summary


def _field_summary(chunks: list, field: str) -> dict[str, int]:
    summary: dict[str, int] = {}
    for chunk in chunks:
        value = getattr(chunk, field, None) or "unknown"
        summary[value] = summary.get(value, 0) + 1
    return summary


def _display_document_status(status: str) -> str:
    return {
        "uploaded": "Uploaded",
        "profiled": "Profiled",
        "extracted": "Evidence Extracted",
        "rules_extracted": "Rules Extracted",
        "normalized": "Ready for Review",
        "ready_for_review": "Ready for Review",
        "processing": "Processing",
        "failed": "Processing Failed",
    }.get(status, status.replace("_", " ").title())


def _document_file_type(document: Document) -> str:
    return document.file_type


def _primary_parser(chunks: list, profiles: list) -> str | None:
    for chunk in chunks:
        if chunk.source_parser:
            return chunk.source_parser
        if chunk.extraction_method:
            return chunk.extraction_method
    for profile in profiles:
        if profile.recommended_extractor:
            return profile.recommended_extractor
    return None


def _review_count(candidates: list, status: str) -> int:
    return sum(1 for candidate in candidates if candidate.review_status == status)


def _last_pipeline_step(document_status: str, chunks: list, candidates: list, normalized_candidates: list) -> str:
    if normalized_candidates:
        return "normalize_candidates"
    if candidates:
        return "extract_rule_candidates"
    if chunks:
        return "extract_structure_evidence"
    if document_status == "profiled":
        return "profile_document"
    return document_status


def _read_quality_report(export_service: LocalExportService, document_id: str) -> dict | None:
    path = export_service.export_path(document_id, "candidate_quality_report")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _next_document_action(profiles: list, chunks: list, candidates: list, normalized_candidates: list) -> dict:
    if not profiles:
        return {"label": "Run Profile", "target_tab": "processing"}
    if not chunks:
        return {"label": "Extract Evidence", "target_tab": "processing"}
    if not candidates:
        return {"label": "Extract Rules", "target_tab": "processing"}
    if not normalized_candidates:
        return {"label": "Normalize Candidates", "target_tab": "processing"}
    if any(candidate.review_status == "pending_review" for candidate in candidates):
        return {"label": "Review rule candidates", "target_tab": "rule_review"}
    return {"label": "View Handoff Package", "target_tab": "handoff"}
