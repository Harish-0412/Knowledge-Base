import logging

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_profile_repository import DocumentProfileRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.extraction_job_repository import ExtractionJobRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository
from app.services.compatiq_semantic_post_processor import CompatIQSemanticPostProcessor
from app.services.candidate_quality_service import CandidateQualityService
from app.services.extraction_router_service import ExtractionRouterService
from app.services.local_export_service import LocalExportService
from app.services.llm_context_pack_builder import LLMContextPackBuilder
from app.services.normalization_service import NormalizationService
from app.services.processing_lane_service import CandidateQualityGate, ProcessingLaneRuleExtractionService
from app.services.profiler_service import ProfilerService
from app.services.rule_extraction_service import RuleExtractionService
from app.core.config import get_settings


class DocIntelPipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.profile_repository = DocumentProfileRepository(db)
        self.chunk_repository = ChunkRepository(db)
        self.candidate_repository = RuleCandidateRepository(db)
        self.job_repository = ExtractionJobRepository(db)
        self.export_service = LocalExportService()
        self.quality_service = CandidateQualityService()

    def run(self, document_id: str) -> dict:
        logger = logging.getLogger(__name__)
        logger.info("docintel pipeline started", extra={"document_id": document_id})
        document = self.document_repository.get_document(document_id)
        if document is None:
            raise AppError(
                code="document_not_found",
                message="Document was not found.",
                status_code=404,
                details={"document_id": document_id},
            )

        warnings: list[str] = []
        profiles = self.profile_repository.list_profiles(document_id)
        if not profiles:
            profiles = self._profile(document)
        else:
            self.export_service.write(document_id, "profile", {"document_id": document_id, "profiles": profiles})

        chunks = self.chunk_repository.list_chunks_for_document(document_id)
        if not chunks:
            chunks, extract_warnings = self._extract(document, profiles)
            warnings.extend(extract_warnings)
        else:
            self.export_service.write_chunks(document_id, chunks)
            self.export_service.write(document_id, "llm_context_pack", LLMContextPackBuilder().build(document_id, chunks))
        if not chunks:
            raise AppError(
                code="no_chunks_found",
                message="Document extraction produced no chunks.",
                status_code=400,
                details={"document_id": document_id},
            )

        candidates, rule_warnings = self._extract_rules(document_id)
        extraction_debug = {}
        if isinstance(rule_warnings, dict):
            extraction_debug = rule_warnings
            rule_warnings = extraction_debug.get("warnings", [])
        warnings.extend(rule_warnings)
        if not candidates:
            warnings.append("No rule candidates were created.")

        normalization_service = NormalizationService()
        normalized_candidates = 0
        needs_human_review = 0
        failed_candidates = 0
        for candidate in candidates:
            normalization_service.normalize_candidate(candidate)
            CandidateQualityGate().apply(candidate, strict=get_settings().quality_gate_strict)
            self.candidate_repository.save(candidate)
            if candidate.normalization_status == "normalized":
                normalized_candidates += 1
                logger.info(
                    "normalization succeeded",
                    extra={"document_id": document_id, "candidate_id": candidate.candidate_id},
                )
            elif candidate.normalization_status == "needs_human_review":
                needs_human_review += 1
                logger.info(
                    "normalization needs human review",
                    extra={"document_id": document_id, "candidate_id": candidate.candidate_id},
                )
            elif candidate.normalization_status == "failed":
                failed_candidates += 1
                logger.info(
                    "normalization failed",
                    extra={"document_id": document_id, "candidate_id": candidate.candidate_id},
                )

        self.document_repository.update_document_status(document_id, "rules_extracted")
        self._export_candidates(document_id, candidates)
        quality_report = self.quality_service.build_report(candidates, warnings)
        self.export_service.write(document_id, "candidate_quality_report", quality_report)
        self.export_service.write(
            document_id,
            "normalization_warnings",
            {"document_id": document_id, "warnings": quality_report["warnings"]},
        )
        export_paths = {
            export_name: self.export_service.export_status(document_id)[export_name]["path"]
            for export_name in self.export_service.EXPORT_FILENAMES
        }
        extractors_used = sorted({chunk.extraction_method for chunk in chunks})

        summary = {
            "document_id": document_id,
            "status": "rules_extracted",
            "profile_count": len(profiles),
            "extractors_used": extractors_used,
            "chunks_created": len(chunks),
            "raw_rule_candidates_created": len(candidates),
            "rule_candidates_created": len(candidates),
            "normalized_rule_candidates_created": normalized_candidates,
            "normalized_candidates": normalized_candidates,
            "needs_human_review": needs_human_review,
            "failed_candidates": failed_candidates,
            "candidate_quality": self.quality_service.summary_metrics(quality_report),
            "pipeline_mode": extraction_debug.get("pipeline_mode", get_settings().extraction_pipeline_mode),
            "total_objects": extraction_debug.get("total_objects", len(chunks)),
            "processing_lane_summary": extraction_debug.get("processing_lane_summary", {}),
            "llm_call_count": extraction_debug.get("llm_call_count", len([chunk for chunk in chunks if chunk.send_to_llm])),
            "deterministic_candidate_count": extraction_debug.get("deterministic_candidate_count", 0),
            "llm_candidate_count": extraction_debug.get("llm_candidate_count", len(candidates)),
            "exports": export_paths,
            "warnings": warnings,
        }
        export_paths["pipeline_summary"] = self.export_service.write(document_id, "pipeline_summary", summary)
        logger.info("docintel pipeline finished", extra=summary)
        return summary

    def _profile(self, document: Document) -> list:
        logging.getLogger(__name__).info("profiling started", extra={"document_id": document.document_id})
        job = self.job_repository.create_running_job(document_id=document.document_id, job_type="profile")
        try:
            profiles = ProfilerService().profile_document(document)
            saved_profiles = self.profile_repository.replace_profiles(document.document_id, profiles)
            self.export_service.write(
                document.document_id,
                "profile",
                {"document_id": document.document_id, "profiles": saved_profiles},
            )
            self.document_repository.update_document_status(document.document_id, "profiled")
            self.job_repository.mark_succeeded(job)
            logging.getLogger(__name__).info(
                "profiling finished",
                extra={"document_id": document.document_id, "profile_count": len(saved_profiles)},
            )
            return saved_profiles
        except Exception as exc:
            self.db.rollback()
            self.job_repository.mark_failed(job, str(exc))
            raise

    def _extract(self, document: Document, profiles: list) -> tuple[list, list[str]]:
        logging.getLogger(__name__).info("extraction started", extra={"document_id": document.document_id})
        job = self.job_repository.create_running_job(document_id=document.document_id, job_type="extract")
        try:
            extracted_blocks, warnings = ExtractionRouterService().extract(document, profiles)
            chunks, chunking_service = CompatIQSemanticPostProcessor().process(document.document_id, extracted_blocks)
            saved_chunks = self.chunk_repository.replace_chunks(document.document_id, chunks)
            self.export_service.write_chunks(document.document_id, saved_chunks)
            self.export_service.write(
                document.document_id,
                "llm_context_pack",
                LLMContextPackBuilder().build(document.document_id, saved_chunks),
            )
            self.export_service.write(
                document.document_id,
                "raw_rule_candidates",
                {"document_id": document.document_id, "rule_candidates": []},
            )
            self.export_service.write(
                document.document_id,
                "normalized_rule_candidates",
                {"document_id": document.document_id, "rule_candidates": []},
            )
            self.export_service.write(document.document_id, "candidate_quality_report", self.quality_service.build_report([]))
            self.export_service.write(document.document_id, "normalization_warnings", {"document_id": document.document_id, "warnings": []})
            self.document_repository.update_document_status(document.document_id, "extracted")
            self.job_repository.mark_succeeded(job)
            logging.getLogger(__name__).info(
                "extraction finished",
                extra={"document_id": document.document_id, "chunks_created": len(saved_chunks)},
            )
            return saved_chunks, warnings
        except Exception as exc:
            self.db.rollback()
            self.job_repository.mark_failed(job, str(exc))
            raise

    def _extract_rules(self, document_id: str) -> tuple[list, list[str] | dict]:
        logging.getLogger(__name__).info("rule extraction started", extra={"document_id": document_id})
        job = self.job_repository.create_running_job(document_id=document_id, job_type="extract_rules")
        try:
            if get_settings().extraction_pipeline_mode == "processing_lanes" and RuleExtractionService.__name__ == "RuleExtractionService":
                candidates, warnings, debug = ProcessingLaneRuleExtractionService(self.db).extract_rules_for_document(document_id)
                debug["warnings"] = warnings
                result_warnings: list[str] | dict = debug
            else:
                candidates, warnings = RuleExtractionService(self.db).extract_rules_for_document(document_id)
                result_warnings = warnings
            self.job_repository.mark_succeeded(job)
            logging.getLogger(__name__).info(
                "rule extraction finished",
                extra={"document_id": document_id, "candidate_count": len(candidates)},
            )
            return candidates, result_warnings
        except Exception as exc:
            self.db.rollback()
            self.job_repository.mark_failed(job, str(exc))
            raise

    def _export_candidates(self, document_id: str, candidates: list) -> None:
        self.export_service.write(
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
        self.export_service.write(
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
