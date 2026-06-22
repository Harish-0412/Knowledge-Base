from collections import Counter
from typing import Any


class CandidateQualityService:
    def build_report(self, candidates: list[Any], warnings: list[str] | None = None) -> dict:
        normalized_payloads = [candidate.normalized_rule_json for candidate in candidates if candidate.normalized_rule_json]
        by_candidate_kind = Counter(payload.get("candidate_kind", "unknown") for payload in normalized_payloads)
        by_rule_type = Counter(payload.get("rule_type", "unknown") for payload in normalized_payloads)
        unknown_component_type_count = 0
        model_as_version_error_count = 0
        missing_candidate_kind_count = 0
        missing_source_page_count = 0
        cisco_ios_xe_semantic_scheme_count = 0
        support_matrix_as_readiness_requirement_count = 0
        requirement_value_raw_is_os_count = 0
        source_pages = []
        needs_human_review_count = 0
        not_a_rule_count = 0
        by_processing_lane = Counter()
        deterministic_candidate_count = 0
        llm_candidate_count = 0

        for candidate, payload in zip(candidates, normalized_payloads, strict=False):
            raw = getattr(candidate, "raw_llm_output_json", {}) or {}
            lane = raw.get("processing_lane") or raw.get("generator") or payload.get("processing_lane") or "unknown"
            by_processing_lane[lane] += 1
            if raw.get("generator") == "deterministic" or str(lane).startswith("deterministic"):
                deterministic_candidate_count += 1
            else:
                llm_candidate_count += 1
            if getattr(candidate, "normalization_status", None) == "needs_human_review":
                needs_human_review_count += 1
            if payload.get("candidate_kind") == "not_a_rule":
                not_a_rule_count += 1
            if not payload.get("candidate_kind"):
                missing_candidate_kind_count += 1
            if payload.get("source_page") is None:
                missing_source_page_count += 1
            else:
                source_pages.append(payload.get("source_page"))
            if "introductory release" in str(payload.get("source_excerpt") or "").lower() and payload.get("rule_type") == "readiness_requirement":
                support_matrix_as_readiness_requirement_count += 1
            for item in (payload.get("conditions") or []) + (payload.get("requirements") or []):
                if item.get("component_type") == "unknown":
                    unknown_component_type_count += 1
                value_raw = str(item.get("value_raw") or "")
                version_raw = str(item.get("version_raw") or "")
                if version_raw and self._looks_like_model(version_raw):
                    model_as_version_error_count += 1
                if item.get("component_type") == "network_os" and item.get("version_scheme") == "semantic":
                    cisco_ios_xe_semantic_scheme_count += 1
                if item.get("component_type") == "network_os" and value_raw.lower() == "os":
                    requirement_value_raw_is_os_count += 1

        report_warnings = list(warnings or [])
        if unknown_component_type_count:
            report_warnings.append(f"{unknown_component_type_count} normalized component values still have component_type=unknown.")
        if model_as_version_error_count:
            report_warnings.append(f"{model_as_version_error_count} model values appear in version fields.")
        if missing_candidate_kind_count:
            report_warnings.append(f"{missing_candidate_kind_count} candidates are missing candidate_kind.")
        if missing_source_page_count:
            report_warnings.append(f"{missing_source_page_count} candidates are missing source_page.")
        if cisco_ios_xe_semantic_scheme_count:
            report_warnings.append(f"{cisco_ios_xe_semantic_scheme_count} Cisco IOS XE versions still use semantic version_scheme.")
        if support_matrix_as_readiness_requirement_count:
            report_warnings.append(f"{support_matrix_as_readiness_requirement_count} introductory-release rows are still readiness_requirement.")
        if requirement_value_raw_is_os_count:
            report_warnings.append(f"{requirement_value_raw_is_os_count} network OS requirements still have value_raw=os.")

        return {
            "document_id": getattr(candidates[0], "document_id", None) if candidates else None,
            "total_candidates": len(candidates),
            "by_candidate_kind": dict(sorted(by_candidate_kind.items())),
            "by_rule_type": dict(sorted(by_rule_type.items())),
            "by_processing_lane": dict(sorted(by_processing_lane.items())),
            "llm_call_count": None,
            "deterministic_candidate_count": deterministic_candidate_count,
            "llm_candidate_count": llm_candidate_count,
            "unknown_component_type_count": unknown_component_type_count,
            "model_as_version_error_count": model_as_version_error_count,
            "missing_candidate_kind_count": missing_candidate_kind_count,
            "missing_source_page_count": missing_source_page_count,
            "source_page_always_one": bool(source_pages) and set(source_pages) == {1},
            "cisco_ios_xe_semantic_scheme_count": cisco_ios_xe_semantic_scheme_count,
            "support_matrix_as_readiness_requirement_count": support_matrix_as_readiness_requirement_count,
            "requirement_value_raw_is_os_count": requirement_value_raw_is_os_count,
            "needs_human_review_count": needs_human_review_count,
            "not_a_rule_count": not_a_rule_count,
            "warnings": report_warnings,
        }

    def summary_metrics(self, report: dict) -> dict:
        return {
            **{kind: report.get("by_candidate_kind", {}).get(kind, 0) for kind in [
                "support_matrix_fact",
                "compliance_rule",
                "unsupported_feature",
                "known_limitation",
                "operational_warning",
                "informational_note",
                "not_a_rule",
            ]},
            "unknown_component_type_count": report.get("unknown_component_type_count", 0),
            "model_as_version_error_count": report.get("model_as_version_error_count", 0),
            "missing_candidate_kind_count": report.get("missing_candidate_kind_count", 0),
            "missing_source_page_count": report.get("missing_source_page_count", 0),
            "source_page_always_one": report.get("source_page_always_one", False),
        }

    def _looks_like_model(self, value: str) -> bool:
        return value.upper().startswith(("C9200", "C9300", "C9500"))
