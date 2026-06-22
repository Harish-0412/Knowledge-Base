import logging
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.config import get_settings
from app.db.models import DocumentChunk, RuleCandidate
from app.prompts.rule_extraction_prompt import build_rule_extraction_prompt
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository
from app.schemas.llm_rule_extraction import LLMExtractionResponse, LLMRuleCandidate
from app.services.json_repair import repair_json
from app.services.llm_context_pack_builder import LLMContextPackBuilder
from app.services.llm_service import LLMService, LLMServiceFactory


logger = logging.getLogger(__name__)


class RuleExtractionService:
    def __init__(self, db: Session, llm_service: LLMService | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        if llm_service is None:
            self._ensure_real_llm_or_explicit_mock_allowed()
        self.llm_service = llm_service or LLMServiceFactory.create()

    def _ensure_real_llm_or_explicit_mock_allowed(self) -> None:
        if self.settings.use_mock_llm and not self.settings.allow_mock_llm_rule_extraction:
            raise AppError(
                code="llm_not_called_mock_mode",
                message=(
                    "Rule extraction is configured to use Mock LLM, so no real Ollama LLM call would be made. "
                    "Set USE_MOCK_LLM=false to call Ollama, or set ALLOW_MOCK_LLM_RULE_EXTRACTION=true only for tests/demos."
                ),
                status_code=400,
                details={
                    "provider": "mock",
                    "use_mock_llm": True,
                    "required_for_real_llm": "USE_MOCK_LLM=false",
                },
            )

    def extract_rules_for_document(self, document_id: str) -> tuple[list[RuleCandidate], list[str]]:
        chunks = ChunkRepository(self.db).list_chunks_for_document(document_id)
        if not chunks:
            raise AppError(
                code="chunks_required",
                message="Document chunks are required before rule extraction.",
                status_code=400,
                details={"document_id": document_id},
            )

        context_pack = LLMContextPackBuilder().build(document_id, chunks)
        candidate_chunks = [chunk for chunk in chunks if chunk.llm_usage == "rule_extraction"]
        metadata_summary = self._document_metadata_summary(chunks)
        warnings: list[str] = []
        if not candidate_chunks:
            return [], ["No likely rule-bearing chunks were found."]

        candidates: list[RuleCandidate] = []
        for iteration, chunk in enumerate(candidate_chunks, 1):
            logger.debug(
                "rule extraction llm call started",
                extra={
                    "document_id": document_id,
                    "chunk_id": chunk.chunk_id,
                    "iteration": iteration,
                    "chunk_type": chunk.chunk_type,
                    "text_preview": chunk.text[:200],
                },
            )
            prompt = build_rule_extraction_prompt(
                document_id=document_id,
                chunk_id=chunk.chunk_id,
                source_excerpt=chunk.source_excerpt,
                chunk_text=chunk.text,
                section_title=chunk.section_title,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number,
                extraction_method=chunk.extraction_method,
                document_metadata_summary=metadata_summary,
            )
            extraction_response, raw_data, error = self._extract_llm_response(prompt)
            if error:
                warnings.append(f"Chunk {chunk.chunk_id}: {error}")
                continue
            logger.debug(
                "rule extraction llm call finished",
                extra={
                    "document_id": document_id,
                    "chunk_id": chunk.chunk_id,
                    "iteration": iteration,
                    "candidate_count": len(extraction_response.rule_candidates),
                    "requirements_preview": [
                        candidate.requirements[0].model_dump() if candidate.requirements else None
                        for candidate in extraction_response.rule_candidates
                    ],
                },
            )

            for candidate_payload in extraction_response.rule_candidates:
                sot_payload = self._stamp_candidate_payload(
                    document_id=document_id,
                    chunk=chunk,
                    payload=candidate_payload,
                    candidate_number=len(candidates) + 1,
                )
                candidates.append(self._build_candidate(document_id, chunk, raw_data, sot_payload))

        self._guard_no_chunk_excerpt_mismatch(candidates)
        saved_candidates = RuleCandidateRepository(self.db).create_many(candidates) if candidates else []
        return saved_candidates, warnings

    def _extract_llm_response(self, prompt: str) -> tuple[LLMExtractionResponse | None, Any | None, str | None]:
        schema = LLMExtractionResponse.model_json_schema()
        raw_output = self.llm_service.generate_json(
            prompt,
            format_schema=schema,
            options={"temperature": 0},
        )
        repair_result = repair_json(raw_output)
        if not repair_result.ok:
            return None, raw_output, repair_result.error

        try:
            return LLMExtractionResponse.model_validate(repair_result.data), repair_result.data, None
        except ValidationError as exc:
            retry_prompt = (
                f"{prompt}\n\nYour previous response failed schema validation with this error: {exc}. "
                "Return corrected JSON only."
            )

        retry_output = self.llm_service.generate_json(
            retry_prompt,
            format_schema=schema,
            options={"temperature": 0},
        )
        retry_repair = repair_json(retry_output)
        if not retry_repair.ok:
            return None, retry_output, retry_repair.error
        try:
            return LLMExtractionResponse.model_validate(retry_repair.data), retry_repair.data, None
        except ValidationError as retry_exc:
            return None, retry_repair.data, f"LLM response failed schema validation after retry: {retry_exc}"

    def _document_metadata_summary(self, chunks: list[DocumentChunk]) -> str:
        metadata_chunks = [chunk for chunk in chunks if chunk.chunk_type == "document_metadata"]
        return "\n".join(chunk.text for chunk in metadata_chunks[:2])[:1500]

    def _stamp_candidate_payload(
        self,
        *,
        document_id: str,
        chunk: DocumentChunk,
        payload: LLMRuleCandidate,
        candidate_number: int,
    ) -> dict:
        candidate_payload = payload.model_dump()
        grounded = self._apply_grounding_check(candidate_payload, chunk.text)
        return {
            "candidate_id": f"RCAND-{candidate_number:06d}",
            "source_document_id": document_id,
            "source_chunk_id": self._public_chunk_id(chunk.chunk_id),
            "source_page": chunk.page_number,
            "source_excerpt": chunk.source_excerpt,
            "candidate_kind": grounded.get("candidate_kind"),
            "rule_type": grounded["rule_type"],
            "condition_logic": grounded["condition_logic"],
            "conditions": self._stamp_conditions(grounded.get("conditions") or []),
            "requirements": self._stamp_requirements(grounded.get("requirements") or []),
            "exceptions": self._stamp_conditions(grounded.get("exceptions") or []),
            "severity": grounded["severity"],
            "confidence_score": grounded["confidence_score"],
            "confidence_reason": grounded.get("confidence_reason"),
            "review_status": grounded["review_status"],
            "remediation_hint": grounded.get("remediation_hint"),
            "tags": grounded["tags"],
            "created_at": datetime.now(UTC).isoformat(),
        }

    def _build_candidate(
        self,
        document_id: str,
        chunk: DocumentChunk,
        raw_data: Any,
        payload: dict,
    ) -> RuleCandidate:
        return RuleCandidate(
            document_id=document_id,
            source_chunk_id=chunk.chunk_id,
            rule_id=payload.get("rule_id"),
            rule_type=payload.get("rule_type"),
            condition_logic=payload.get("condition_logic"),
            conditions_json=payload.get("conditions"),
            requirement_json=payload.get("requirements"),
            severity=payload.get("severity"),
            confidence_score=self._coerce_float(payload.get("confidence_score")),
            confidence_reason=payload.get("confidence_reason"),
            explanation=payload.get("remediation_hint"),
            source_excerpt=chunk.source_excerpt,
            review_status=payload.get("review_status") or "pending_review",
            normalization_status="pending_normalization",
            raw_llm_output_json={"rule_candidates": [payload], "llm_response": raw_data},
            normalized_rule_json=None,
            validation_errors_json=None,
        )

    def _guard_no_chunk_excerpt_mismatch(self, candidates: list[RuleCandidate]) -> None:
        excerpts_by_chunk: dict[int, str] = {}
        for candidate in candidates:
            existing = excerpts_by_chunk.setdefault(candidate.source_chunk_id, candidate.source_excerpt)
            if existing != candidate.source_excerpt:
                raise AppError(
                    code="source_excerpt_chunk_mismatch",
                    message=(
                        "Rule extraction produced multiple source excerpts for the same chunk_id. "
                        "This indicates table rows were duplicated after a shared LLM call."
                    ),
                    status_code=500,
                    details={
                        "source_chunk_id": candidate.source_chunk_id,
                        "first_source_excerpt": existing[:200],
                        "conflicting_source_excerpt": candidate.source_excerpt[:200],
                    },
                )

    def _stamp_conditions(self, items: list[dict]) -> list[dict]:
        stamped = []
        for index, item in enumerate(items, 1):
            stamped_item = dict(item)
            stamped_item["condition_id"] = f"COND-{index:03d}"
            stamped.append(stamped_item)
        return stamped

    def _stamp_requirements(self, items: list[dict]) -> list[dict]:
        stamped = []
        for index, item in enumerate(items, 1):
            stamped_item = dict(item)
            stamped_item.pop("vendor", None)
            stamped_item["requirement_id"] = f"REQ-{index:03d}"
            stamped.append(stamped_item)
        return stamped

    def _apply_grounding_check(self, payload: dict, chunk_text: str) -> dict:
        checked = dict(payload)
        checked["review_status"] = "pending_review"
        checked["tags"] = []
        missing_values = [
            str(value)
            for value in self._raw_values(checked)
            if value is not None and str(value).strip() and not self._contains_normalized(chunk_text, str(value))
        ]
        if missing_values:
            checked["confidence_score"] = min(self._coerce_float(checked.get("confidence_score")) or 0.0, 0.3)
            checked["confidence_reason"] = (
                f"{checked.get('confidence_reason') or ''} "
                "[AUTO-FLAGGED: extracted value not found verbatim in source chunk text - verify before approving.]"
            ).strip()
            checked["review_status"] = "needs_clarification"
            checked["tags"] = ["unverified_value"]
        return checked

    def _raw_values(self, payload: dict) -> list[Any]:
        values: list[Any] = []
        for group_name in ("conditions", "requirements", "exceptions"):
            for item in payload.get(group_name) or []:
                if isinstance(item, dict):
                    values.extend([item.get("version_raw"), item.get("value_raw")])
        return values

    def _contains_normalized(self, text: str, value: str) -> bool:
        return self._normalize_for_grounding(value) in self._normalize_for_grounding(text)

    def _normalize_for_grounding(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    def _public_chunk_id(self, chunk_id: int) -> str:
        return f"CHUNK-{chunk_id:06d}"

    def _coerce_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
