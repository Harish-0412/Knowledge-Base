import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DocumentChunk, RuleCandidate
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository
from app.services.cisco_normalization import (
    is_cisco_network_module,
    is_cisco_switch_model,
    parse_cisco_ios_xe_release,
)
from app.services.local_export_service import LocalExportService
from app.services.llm_context_pack_builder import LLMContextPackBuilder
from app.services.rule_extraction_service import RuleExtractionService


PROCESSING_LANES = [
    "deterministic_support_matrix",
    "deterministic_table_rule",
    "llm_prose_rule",
    "context_only",
    "evidence_only",
    "ignore",
]


@dataclass
class LaneDecision:
    processing_lane: str
    table_schema_type: str = "unknown_table"
    confidence: float = 0.0
    reason: str = ""
    detected_headers: list[str] = field(default_factory=list)
    generator: str | None = None


class TableSchemaClassifier:
    def classify(self, chunk: DocumentChunk) -> LaneDecision:
        text = self._chunk_text(chunk)
        headers = self._headers(chunk, text)
        normalized_headers = " ".join(headers).lower()

        if "switch model" in text.lower() and "introductory release" in text.lower():
            return LaneDecision(
                processing_lane="deterministic_support_matrix",
                table_schema_type="cisco_switch_model_introductory_release",
                confidence=0.95,
                reason="Detected Switch Model and Introductory Release fields.",
                detected_headers=headers,
                generator="cisco_switch_model_intro_release",
            )
        if "network module" in text.lower() and "introductory release" in text.lower():
            return LaneDecision(
                processing_lane="deterministic_support_matrix",
                table_schema_type="cisco_network_module_introductory_release",
                confidence=0.95,
                reason="Detected Network Module and Introductory Release fields.",
                detected_headers=headers,
                generator="cisco_network_module_intro_release",
            )
        if "not supported" in text.lower() and ("feature" in normalized_headers or text.lower().startswith("feature:")):
            return LaneDecision(
                processing_lane="deterministic_table_rule",
                table_schema_type="unsupported_feature_matrix",
                confidence=0.9,
                reason="Detected unsupported feature row.",
                detected_headers=headers,
                generator="unsupported_feature",
            )
        if "rommon" in normalized_headers and "version" in normalized_headers:
            return LaneDecision(
                processing_lane="deterministic_support_matrix",
                table_schema_type="rommon_version_matrix",
                confidence=0.75,
                reason="Detected ROMMON version table shape.",
                detected_headers=headers,
            )
        return LaneDecision(
            processing_lane="llm_prose_rule" if self._has_rule_language(text) else "evidence_only",
            table_schema_type="unknown_table",
            confidence=0.4,
            reason="No deterministic table schema matched.",
            detected_headers=headers,
        )

    def _chunk_text(self, chunk: DocumentChunk) -> str:
        return " ".join(str(part or "") for part in [chunk.section_title, chunk.source_excerpt, chunk.text]).strip()

    def _headers(self, chunk: DocumentChunk, text: str) -> list[str]:
        if chunk.table_headers_json:
            return [str(header) for header in chunk.table_headers_json]
        return re.findall(r"([A-Z][A-Za-z0-9 /()+-]{2,40}):", text)

    def _has_rule_language(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            term in lowered
            for term in [
                "must",
                "required",
                "requires",
                "not supported",
                "not allowed",
                "earlier than",
                "do not",
                "before upgrading",
                "limitation",
                "restriction",
            ]
        )


class ProcessingLaneRouter:
    def __init__(self, classifier: TableSchemaClassifier | None = None) -> None:
        self.classifier = classifier or TableSchemaClassifier()

    def route(self, chunk: DocumentChunk) -> LaneDecision:
        text = f"{chunk.section_title or ''} {chunk.source_excerpt or ''} {chunk.text or ''}".lower()
        if self._is_junk(text):
            return LaneDecision("ignore", "unknown_table", 0.9, "Ignored boilerplate or junk chunk.")
        if chunk.semantic_zone in {"document_metadata", "overview", "title"}:
            return LaneDecision("context_only", "unknown_table", 0.8, "Metadata or overview context.")
        return self.classifier.classify(chunk)

    def _is_junk(self, text: str) -> bool:
        compact = re.sub(r"\s+", " ", text).strip()
        if not compact:
            return True
        return compact in {"copyright", "table of contents"} or bool(re.fullmatch(r"\d{1,4}", compact))


class DeterministicCandidateGenerator:
    def generate(self, document_id: str, chunk: DocumentChunk, decision: LaneDecision) -> list[RuleCandidate]:
        if decision.generator == "cisco_switch_model_intro_release":
            payload = self._cisco_intro_payload(chunk, model_key="Switch Model", rule_type="model_support_min_version")
        elif decision.generator == "cisco_network_module_intro_release":
            payload = self._cisco_intro_payload(chunk, model_key="Network Module", rule_type="network_module_support_min_version")
        elif decision.generator == "unsupported_feature":
            payload = self._unsupported_feature_payload(chunk)
        else:
            return []
        if not payload:
            return []
        payload["source_document_id"] = document_id
        payload["source_chunk_id"] = f"CHUNK-{chunk.chunk_id:06d}" if chunk.chunk_id is not None else "CHUNK-000000"
        payload["source_page"] = chunk.page_number
        payload["source_excerpt"] = chunk.source_excerpt
        payload["review_status"] = "pending_review"
        payload["created_at"] = datetime.now(UTC).isoformat()
        payload["processing_lane"] = decision.processing_lane
        return [
            RuleCandidate(
                document_id=document_id,
                source_chunk_id=chunk.chunk_id or 0,
                rule_type=payload["rule_type"],
                condition_logic=payload["condition_logic"],
                conditions_json=payload["conditions"],
                requirement_json=payload["requirements"],
                severity=payload["severity"],
                confidence_score=payload["confidence_score"],
                confidence_reason=payload["confidence_reason"],
                explanation=payload.get("remediation_hint"),
                source_excerpt=chunk.source_excerpt,
                review_status="pending_review",
                normalization_status="pending_normalization",
                raw_llm_output_json={"rule_candidates": [payload], "generator": "deterministic", "processing_lane": decision.processing_lane},
                normalized_rule_json=None,
                validation_errors_json=None,
            )
        ]

    def _cisco_intro_payload(self, chunk: DocumentChunk, *, model_key: str, rule_type: str) -> dict | None:
        text = chunk.source_excerpt or chunk.text
        model = self._field(text, model_key)
        release_text = self._field(text, "Introductory Release")
        if not model or not release_text:
            return None
        release = parse_cisco_ios_xe_release(release_text)
        component_type = "network_module" if model_key == "Network Module" else "device_model"
        family = "Cisco Catalyst Network Module" if component_type == "network_module" else "Cisco Catalyst 9200 Series"
        name = model if component_type == "network_module" else "Cisco Catalyst 9200 Series Switch"
        return {
            "candidate_kind": "support_matrix_fact",
            "rule_type": rule_type,
            "condition_logic": "AND",
            "conditions": [
                {
                    "component_type": component_type,
                    "component_name": name,
                    "component_family": family,
                    "vendor": "Cisco",
                    "operator": "==",
                    "value_raw": model,
                    "version_raw": None,
                    "version_scheme": None,
                }
            ],
            "requirements": [
                {
                    "component_type": "network_os",
                    "component_name": "Cisco IOS XE",
                    "component_family": release["component_family"],
                    "operator": ">=",
                    "value_raw": None,
                    "version_raw": release["version_raw"],
                    "version_scheme": release["version_scheme"],
                    "requirement_kind": "min_version",
                }
            ],
            "exceptions": [],
            "severity": "info",
            "confidence_score": 0.78,
            "confidence_reason": "The source table lists the introductory Cisco IOS XE release. This is interpreted as first supported release and should be human-reviewed before enforcement.",
            "remediation_hint": f"Ensure {release_text} or later is installed for {model}.",
            "tags": ["cisco", "support_matrix", "ios_xe"],
        }

    def _unsupported_feature_payload(self, chunk: DocumentChunk) -> dict | None:
        text = chunk.source_excerpt or chunk.text
        feature = self._field(text, "Feature") or text.split("|")[0].replace("Feature:", "").strip()
        if not feature:
            return None
        return {
            "candidate_kind": "unsupported_feature",
            "rule_type": "unsupported_feature",
            "condition_logic": "AND",
            "conditions": [
                {
                    "component_type": "device_family",
                    "component_name": "Cisco Catalyst 9200 Series Switches",
                    "operator": "installed",
                    "value_raw": "Cisco Catalyst 9200 Series Switches",
                }
            ],
            "requirements": [
                {
                    "component_type": "feature",
                    "component_name": feature,
                    "operator": "not_supported",
                    "value_raw": feature,
                    "requirement_kind": "not_supported",
                }
            ],
            "exceptions": [],
            "severity": "warning",
            "confidence_score": 0.9,
            "confidence_reason": "The source explicitly marks this feature as not supported.",
            "remediation_hint": f"{feature} is not supported for this platform family.",
            "tags": ["unsupported_feature"],
        }

    def _field(self, text: str, field: str) -> str | None:
        match = re.search(rf"{re.escape(field)}:\s*(.*?)(?:\s+\|\s+[A-Z][A-Za-z0-9 /()+-]{{2,40}}:|$)", text)
        if not match:
            return None
        return match.group(1).strip()


class CandidateQualityGate:
    SERIOUS_WARNINGS = {
        "missing_candidate_kind",
        "unknown_component_type",
        "model_as_version_error",
        "source_page_missing",
        "support_matrix_as_readiness_requirement",
    }

    def evaluate(self, candidate: RuleCandidate) -> list[str]:
        payload = candidate.normalized_rule_json if isinstance(candidate.normalized_rule_json, dict) else {}
        warnings: list[str] = []
        if not payload.get("candidate_kind"):
            warnings.append("missing_candidate_kind")
        if payload.get("source_page") is None:
            warnings.append("source_page_missing")
        if self._source_text(candidate).lower().find("introductory release") >= 0 and payload.get("rule_type") == "readiness_requirement":
            warnings.append("support_matrix_as_readiness_requirement")
        for item in (payload.get("conditions") or []) + (payload.get("requirements") or []):
            if item.get("component_type") == "unknown":
                warnings.append("unknown_component_type")
            if self._looks_like_model(item.get("version_raw")):
                warnings.append("model_as_version_error")
            if item.get("component_type") == "network_os" and item.get("version_scheme") == "semantic":
                warnings.append("cisco_ios_xe_semantic_version_scheme")
            if item.get("component_type") == "network_os" and str(item.get("value_raw") or "").lower() == "os":
                warnings.append("requirement_value_raw_is_os")
        return sorted(set(warnings))

    def apply(self, candidate: RuleCandidate, *, strict: bool = False) -> RuleCandidate:
        warnings = self.evaluate(candidate)
        existing = candidate.validation_errors_json or []
        if not isinstance(existing, list):
            existing = [existing]
        warning_items = [{"code": warning, "message": warning.replace("_", " ")} for warning in warnings]
        candidate.validation_errors_json = existing + warning_items
        if warnings and (set(warnings) & self.SERIOUS_WARNINGS or strict):
            candidate.normalization_status = "needs_human_review"
        return candidate

    def _source_text(self, candidate: RuleCandidate) -> str:
        return " ".join(str(part or "") for part in [candidate.source_excerpt, getattr(candidate.source_chunk, "text", "")])

    def _looks_like_model(self, value: Any) -> bool:
        text = str(value or "").strip()
        return is_cisco_switch_model(text) or is_cisco_network_module(text)


class ProcessingLaneRuleExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.router = ProcessingLaneRouter()
        self.generator = DeterministicCandidateGenerator()
        self.export_service = LocalExportService()

    def extract_rules_for_document(self, document_id: str) -> tuple[list[RuleCandidate], list[str], dict]:
        chunks = ChunkRepository(self.db).list_chunks_for_document(document_id)
        warnings: list[str] = []
        decisions: dict[int, LaneDecision] = {}
        deterministic_candidates: list[RuleCandidate] = []
        lane_counts: Counter[str] = Counter()

        for chunk in chunks:
            decision = self.router.route(chunk)
            decisions[chunk.chunk_id] = decision
            lane_counts[decision.processing_lane] += 1
            self._annotate_chunk(chunk, decision)
            if decision.processing_lane.startswith("deterministic") and self.settings.enable_deterministic_table_extraction:
                deterministic_candidates.extend(self.generator.generate(document_id, chunk, decision))
        self.db.commit()

        llm_candidates: list[RuleCandidate] = []
        llm_call_log = {"llm_call_count": 0, "calls": []}
        if self.settings.enable_llm_prose_extraction or self.settings.enable_llm_table_extraction:
            llm_chunks = [chunk for chunk in chunks if self._send_to_llm(decisions[chunk.chunk_id])]
            if llm_chunks:
                llm_candidates, llm_warnings = RuleExtractionService(self.db).extract_rules_for_document(document_id)
                warnings.extend(llm_warnings)
                llm_call_log = {
                    "llm_call_count": len(llm_chunks),
                    "calls": [
                        {
                            "section_title": chunk.section_title,
                            "source_pages": [chunk.page_number],
                            "input_char_count": len(chunk.text or ""),
                            "candidate_count": None,
                        }
                        for chunk in llm_chunks
                    ],
                }

        saved_deterministic = RuleCandidateRepository(self.db).create_many(deterministic_candidates) if deterministic_candidates else []
        saved = saved_deterministic + llm_candidates
        debug = {
            "pipeline_mode": "processing_lanes",
            "total_objects": len(chunks),
            "processing_lane_summary": {lane: lane_counts.get(lane, 0) for lane in PROCESSING_LANES},
            "llm_call_count": llm_call_log["llm_call_count"],
            "deterministic_candidate_count": len(deterministic_candidates),
            "llm_candidate_count": len(llm_candidates),
            "llm_call_log": llm_call_log,
            "processing_lane_report": {
                "document_id": document_id,
                "objects": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "page_number": chunk.page_number,
                        "processing_lane": decisions[chunk.chunk_id].processing_lane,
                        "table_schema_type": decisions[chunk.chunk_id].table_schema_type,
                        "confidence": decisions[chunk.chunk_id].confidence,
                        "reason": decisions[chunk.chunk_id].reason,
                    }
                    for chunk in chunks
                ],
            },
        }
        self._write_debug_exports(document_id, chunks, deterministic_candidates, debug)
        return saved, warnings, debug

    def _annotate_chunk(self, chunk: DocumentChunk, decision: LaneDecision) -> None:
        metadata = dict(chunk.metadata_json or {})
        metadata.update(
            {
                "processing_lane": decision.processing_lane,
                "table_schema_type": decision.table_schema_type,
                "structure_confidence_score": decision.confidence,
                "processing_lane_reason": decision.reason,
                "detected_headers": decision.detected_headers,
            }
        )
        chunk.metadata_json = metadata
        chunk.llm_usage = "rule_extraction" if self._send_to_llm(decision) else decision.processing_lane
        chunk.send_to_llm = self._send_to_llm(decision)

    def _send_to_llm(self, decision: LaneDecision) -> bool:
        if decision.processing_lane == "llm_prose_rule":
            return self.settings.enable_llm_prose_extraction
        if decision.processing_lane.startswith("deterministic"):
            return not self.settings.enable_deterministic_table_extraction and self.settings.enable_llm_table_extraction
        return False

    def _write_debug_exports(self, document_id: str, chunks: list[DocumentChunk], deterministic_candidates: list[RuleCandidate], debug: dict) -> None:
        if not self.settings.export_pipeline_debug_files:
            return
        self.export_service.write(document_id, "document_objects", {"document_id": document_id, "objects": [self._object_payload(chunk) for chunk in chunks]})
        self.export_service.write(document_id, "processing_lane_report", debug["processing_lane_report"])
        self.export_service.write(
            document_id,
            "deterministic_candidates",
            {"document_id": document_id, "rule_candidates": [candidate.raw_llm_output_json for candidate in deterministic_candidates]},
        )
        self.export_service.write(document_id, "llm_sections", {"document_id": document_id, "sections": debug["llm_call_log"]["calls"]})
        self.export_service.write(document_id, "llm_call_log", debug["llm_call_log"])

    def _object_payload(self, chunk: DocumentChunk) -> dict:
        return {
            "chunk_id": chunk.chunk_id,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
            "processing_lane": (chunk.metadata_json or {}).get("processing_lane"),
            "table_schema_type": (chunk.metadata_json or {}).get("table_schema_type"),
            "source_excerpt": chunk.source_excerpt,
            "send_to_llm": chunk.send_to_llm,
            "llm_usage": chunk.llm_usage,
        }
