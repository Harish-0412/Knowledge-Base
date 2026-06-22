import re
from datetime import UTC, datetime
from typing import Any

from app.db.models import RuleCandidate
from app.services.cisco_normalization import (
    is_cisco_network_module,
    is_cisco_switch_model,
    parse_cisco_ios_xe_release,
)
from app.services.schema_validation_service import SchemaValidationService


COMPONENT_ALIASES = {
    "bios": "bios",
    "system bios": "bios",
    "dell bios": "bios",
    "os": "os",
    "operating system": "os",
    "firmware": "firmware",
    "driver": "driver",
    "cpu": "cpu",
    "processor": "cpu",
    "hba": "hba",
    "host bus adapter": "hba",
    "raid": "raid_controller",
    "perc": "raid_controller",
    "raid controller": "raid_controller",
    "agent": "agent",
    "endpoint agent": "agent",
    "security agent": "agent",
    "management tool": "management_tool",
    "model": "device_model",
    "switch model": "device_model",
    "hardware model": "device_model",
    "device model": "device_model",
    "switch": "device",
    "device_type": "device_family",
    "network module": "network_module",
    "module": "network_module",
    "cisco ios xe": "network_os",
    "ios xe": "network_os",
    "switch software": "network_os",
    "software image": "software_image",
    "rommon": "bootloader",
    "bootloader": "bootloader",
    "license": "license",
    "license level": "license",
    "feature": "feature",
    "unsupported feature": "feature",
    "virtualization_feature": "feature",
    "transceiver": "transceiver",
    "optic": "transceiver",
}

OPERATOR_ALIASES = {
    "or later": ">=",
    "minimum": ">=",
    "at least": ">=",
    "not earlier than": ">=",
    "earlier than": "<",
    "below": "<",
    "older than": "<",
    "equal to": "==",
    "not supported": "not_supported",
    "incompatible": "not_in",
    "incompatible_with": "not_in",
    "must not": "must_not",
    "do not": "must_not",
    ">=": ">=",
    "<=": "<=",
    ">": ">",
    "<": "<",
    "==": "==",
    "installed": "installed",
    "requires": ">=",
}

RULE_TYPE_ALIASES = {
    "requires_minimum_version": "min_version_constraint",
    "minimum_version": "min_version_constraint",
    "min_version_constraint": "min_version_constraint",
    "feature_support_added": "feature_support_added",
    "added_support": "feature_support_added",
    "known_issue_fixed": "known_issue_fixed",
    "fixed_issue": "known_issue_fixed",
    "incompatible_with": "incompatible_combination",
    "incompatible_combination": "incompatible_combination",
    "unsupported_combination": "incompatible_combination",
    "update_order_constraint": "update_order_constraint",
    "upgrade_order_constraint": "upgrade_order_constraint",
    "readiness_requirement": "readiness_requirement",
    "model_support_min_version": "model_support_min_version",
    "network_module_support_min_version": "network_module_support_min_version",
    "license_support_fact": "license_support_fact",
    "software_image_fact": "software_image_fact",
    "rommon_version_fact": "rommon_version_fact",
    "unsupported_feature": "unsupported_feature",
    "configuration_requirement": "configuration_requirement",
    "operational_warning": "operational_warning",
    "known_limitation": "known_limitation",
    "not_a_rule": "not_a_rule",
}

CANDIDATE_KINDS = {
    "support_matrix_fact",
    "compliance_rule",
    "unsupported_feature",
    "known_limitation",
    "operational_warning",
    "informational_note",
    "not_a_rule",
}

SEVERITY_ALIASES = {
    "critical": "critical",
    "high": "critical",
    "blocker": "blocker",
    "warning": "warning",
    "medium": "warning",
    "low": "info",
    "info": "info",
    "unknown": "info",
}


class NormalizationService:
    def __init__(self, validation_service: SchemaValidationService | None = None) -> None:
        self.validation_service = validation_service or SchemaValidationService()

    def normalize_candidate(self, candidate: RuleCandidate) -> RuleCandidate:
        payload = self._candidate_payload(candidate)
        conditions = self._normalize_conditions(payload.get("conditions") or candidate.conditions_json or [])
        requirements = self._normalize_requirements(
            payload.get("requirements") or payload.get("requirement") or candidate.requirement_json or {},
            candidate.source_excerpt,
        )
        source_text = self._source_text(candidate, payload)
        rule_type = self._normalize_rule_type(payload.get("rule_type") or candidate.rule_type, source_text)
        candidate_kind = self._candidate_kind(payload, rule_type, source_text)
        severity = self._normalize_severity(payload.get("severity") or candidate.severity)
        condition_logic = self._normalize_condition_logic(payload.get("condition_logic") or candidate.condition_logic)
        confidence_score = self._confidence(candidate.confidence_score)
        confidence_reason = candidate.confidence_reason

        if candidate_kind == "support_matrix_fact":
            confidence_score = min(confidence_score or 0.78, 0.8)
            confidence_reason = (
                "The source table lists an introductory Cisco IOS XE release. "
                "This is interpreted as first supported software version and should be human-reviewed before enforcement."
            )
        elif candidate_kind == "unsupported_feature":
            severity = "warning" if severity == "info" else severity

        normalized = {
            "candidate_id": self._public_candidate_id(candidate.candidate_id),
            "source_document_id": candidate.document_id,
            "source_chunk_id": self._public_chunk_id(candidate.source_chunk_id),
            "source_page": self._source_page(candidate, payload),
            "source_excerpt": candidate.source_excerpt,
            "candidate_kind": candidate_kind,
            "rule_type": rule_type,
            "condition_logic": condition_logic,
            "conditions": conditions,
            "requirements": requirements,
            "exceptions": [],
            "severity": severity,
            "confidence_score": confidence_score,
            "confidence_reason": confidence_reason,
            "review_status": payload.get("review_status") or candidate.review_status or "pending_review",
            "remediation_hint": payload.get("remediation_hint") or payload.get("explanation") or candidate.explanation,
            "tags": self._tags(payload, candidate_kind),
            "created_at": datetime.now(UTC).isoformat(),
        }

        valid, errors = self.validation_service.validate_normalized_candidate(normalized)
        ambiguous = self._has_ambiguous_values(conditions, requirements)

        candidate.rule_type = rule_type
        candidate.condition_logic = condition_logic
        candidate.conditions_json = conditions
        candidate.requirement_json = requirements
        candidate.severity = severity
        candidate.normalized_rule_json = normalized
        candidate.validation_errors_json = errors
        uncertain = self._has_uncertain_values(conditions, requirements)
        candidate.normalization_status = "normalized" if valid and not ambiguous and not uncertain else "needs_human_review"
        if ambiguous and not errors:
            candidate.validation_errors_json = [{"message": "One or more values could not be confidently normalized."}]
        elif uncertain and not errors:
            candidate.validation_errors_json = [{"message": "One or more Cisco IOS XE versions could not be confidently parsed."}]
        return candidate

    def _candidate_payload(self, candidate: RuleCandidate) -> dict:
        raw = candidate.raw_llm_output_json
        if isinstance(raw, dict):
            payloads = raw.get("rule_candidates")
            if isinstance(payloads, list) and payloads and isinstance(payloads[0], dict):
                return payloads[0]
        return {
            "rule_type": candidate.rule_type,
            "condition_logic": candidate.condition_logic,
            "conditions": candidate.conditions_json,
            "requirements": candidate.requirement_json,
            "severity": candidate.severity,
            "explanation": candidate.explanation,
            "confidence_score": candidate.confidence_score,
            "confidence_reason": candidate.confidence_reason,
            "review_status": candidate.review_status,
        }

    def _normalize_conditions(self, raw_conditions: Any) -> list[dict]:
        if isinstance(raw_conditions, dict):
            raw_conditions = [raw_conditions]
        if not isinstance(raw_conditions, list):
            raw_conditions = []
        if not raw_conditions:
            raw_conditions = [{"field": "unknown", "operator": "installed", "value": None}]

        return [self._normalize_component_item(item, f"COND-{index:03d}", condition=True) for index, item in enumerate(raw_conditions, 1)]

    def _normalize_requirements(self, raw_requirement: Any, source_excerpt: str) -> list[dict]:
        raw_requirements = raw_requirement if isinstance(raw_requirement, list) else [raw_requirement]
        normalized = []
        for index, item in enumerate(raw_requirements, 1):
            if not isinstance(item, dict):
                item = {"field": "unknown", "operator": "exists", "value": item}
            requirement = self._normalize_component_item(
                item,
                f"REQ-{index:03d}",
                condition=False,
                context=source_excerpt,
            )
            operator_kind = self._requirement_kind(requirement["operator"])
            requirement["requirement_kind"] = operator_kind if operator_kind == "not_supported" else item.get("requirement_kind") or operator_kind
            normalized.append(requirement)
        return normalized

    def _normalize_component_item(self, item: dict, item_id: str, *, condition: bool, context: str = "") -> dict:
        field = str(item.get("field") or item.get("component_type") or item.get("component_name") or "")
        value = item.get("value_raw") if "value_raw" in item else item.get("value")
        raw_text = " ".join(
            str(part)
            for part in [
                field,
                item.get("component_name"),
                item.get("component_family"),
                item.get("operator"),
                value,
                item.get("version_raw"),
                context,
            ]
            if part is not None
        )
        component_type = self._normalize_component_type(str(item.get("component_type") or field), value, raw_text)
        operator = self._normalize_operator(str(item.get("operator") or raw_text or "installed"))
        cisco_release = parse_cisco_ios_xe_release(raw_text) if "cisco ios xe" in raw_text.lower() else None
        if cisco_release and cisco_release["version_raw"]:
            component_type = "network_os"
        version_raw = cisco_release["version_raw"] if cisco_release and cisco_release["version_raw"] else item.get("version_raw") or self._extract_version_raw(value, raw_text)
        version_normalized, version_scheme = self._normalize_version(version_raw, raw_text)
        value_raw = value if value is not None else field or None
        value_normalized = self._normalize_value(value_raw)
        component_name = item.get("component_name") or self._component_name(field, value, component_type)
        component_family = item.get("component_family") or self._component_family(value)

        if cisco_release and cisco_release["version_raw"]:
            component_name = "Cisco IOS XE"
            component_family = cisco_release["component_family"]
            version_raw = cisco_release["version_raw"]
            version_normalized = cisco_release["version_normalized"]
            version_scheme = cisco_release["version_scheme"]
            if not condition:
                value_raw = None
                value_normalized = None

        model_value = self._model_value(item, value, component_name)
        if model_value and is_cisco_switch_model(model_value):
            component_type = "device_model"
            if condition and operator == "installed":
                operator = "=="
            component_name = "Cisco Catalyst 9200 Series Switch" if model_value.upper().startswith("C9200") else component_name
            component_family = "Cisco Catalyst 9200 Series" if model_value.upper().startswith("C9200") else component_family
            value_raw = model_value
            value_normalized = self._normalize_value(model_value)
            version_raw = None
            version_normalized = None
            version_scheme = None
        elif model_value and is_cisco_network_module(model_value):
            component_type = "network_module"
            if condition and operator == "installed":
                operator = "=="
            component_name = model_value
            component_family = "Cisco Catalyst Network Module"
            value_raw = model_value
            value_normalized = self._normalize_value(model_value)
            version_raw = None
            version_normalized = None
            version_scheme = None

        if component_type == "network_os" and value_raw in {"os", "network_os"}:
            value_raw = None
            value_normalized = None

        final_version_scheme = version_scheme if cisco_release and cisco_release["version_raw"] else item.get("version_scheme") or version_scheme
        normalized = {
            "component_type": component_type,
            "operator": operator,
            "component_name": component_name,
            "component_family": component_family,
            "value_raw": value_raw,
            "value_normalized": value_normalized,
            "version_raw": version_raw,
            "version_normalized": version_normalized,
            "version_scheme": final_version_scheme,
            "metadata": {"raw": item},
        }
        if model_value and component_type in {"device_model", "network_module"}:
            normalized["metadata"]["model"] = model_value
        if condition:
            normalized["condition_id"] = item_id
            normalized["vendor"] = item.get("vendor")
        else:
            normalized["requirement_id"] = item_id
        return normalized

    def _normalize_component_type(self, field: str, value: Any, raw_text: str) -> str:
        primary = f"{field} {value or ''}".lower()
        haystack = f"{primary} {raw_text}".lower()
        if is_cisco_switch_model(value) or is_cisco_switch_model(field):
            return "device_model"
        if is_cisco_network_module(value) or is_cisco_network_module(field):
            return "network_module"
        if "cisco ios xe" in haystack:
            return "network_os"
        if "windows server" in primary or "vmware esxi" in primary:
            return "os"
        for alias, normalized in COMPONENT_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", primary):
                return normalized
        for alias, normalized in COMPONENT_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", haystack):
                return normalized
        if "windows server" in haystack or "vmware esxi" in haystack:
            return "os"
        return "unknown"

    def _normalize_operator(self, operator: str) -> str:
        lowered = operator.lower()
        for alias, normalized in OPERATOR_ALIASES.items():
            if alias in lowered:
                return normalized
        return "installed"

    def _normalize_rule_type(self, rule_type: Any, source_text: str = "") -> str:
        text = source_text.lower()
        if "switch model" in text and "introductory release" in text:
            return "model_support_min_version"
        if "network module" in text and "introductory release" in text:
            return "network_module_support_min_version"
        if "not supported" in text:
            return "unsupported_feature"
        if "do not" in text or "must not" in text:
            return "operational_warning"
        lowered = str(rule_type or "").lower()
        return RULE_TYPE_ALIASES.get(lowered, "min_version_constraint")

    def _normalize_severity(self, severity: Any) -> str:
        lowered = str(severity or "unknown").lower()
        return SEVERITY_ALIASES.get(lowered, "info")

    def _normalize_condition_logic(self, condition_logic: Any) -> str:
        lowered = str(condition_logic or "AND").lower()
        return "OR" if lowered == "or" or lowered == "any" else "AND"

    def _extract_version_raw(self, value: Any, raw_text: str) -> str | None:
        text = str(value if value is not None else raw_text)
        if is_cisco_switch_model(text) or is_cisco_network_module(text):
            return None
        version_match = re.search(r"\bv?\d+(?:\.\d+)+(?:\.x|[a-z])?\b", text, flags=re.IGNORECASE)
        if version_match:
            return version_match.group(0)
        named_patterns = [r"Windows Server \d{4}(?: R2)?", r"VMware ESXi \d+(?:\.\d+)?\.x"]
        for pattern in named_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _normalize_version(self, version_raw: str | None, context: str = "") -> tuple[str | None, str | None]:
        if not version_raw:
            return None, None
        raw = version_raw.strip()
        if "cisco ios xe" in context.lower() or re.match(r"^\d+(?:\.\d+){1,3}[a-z]?$", raw, flags=re.IGNORECASE):
            if re.match(r"^\d+(?:\.\d+){1,3}[a-z]?$", raw, flags=re.IGNORECASE):
                if "cisco ios xe" in context.lower():
                    return raw, "cisco_ios_xe"
                parts = [str(int(part)) for part in raw.split(".")]
                return ".".join(parts), "semantic"
            return self._slug(raw), "cisco_ios_xe_unknown"
        if re.search(r"[A-Za-z]", raw) and not re.match(r"^v?\d", raw, flags=re.IGNORECASE):
            return self._slug(raw), "named_release"
        cleaned = raw.lstrip("vV")
        if cleaned.lower().endswith(".x"):
            return cleaned, "wildcard"
        if re.match(r"^\d+(?:\.\d+)+$", cleaned):
            parts = [str(int(part)) for part in cleaned.split(".")]
            return ".".join(parts), "semantic"
        return self._slug(raw), "named_release"

    def _normalize_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (int, float, bool)):
            return value
        if str(value).lower() in {"os", "network_os"}:
            return None
        return self._slug(str(value))

    def _component_name(self, field: str, value: Any, component_type: str) -> str | None:
        if component_type == "unknown":
            return str(field or value) if field or value else None
        if component_type == "network_os":
            return "Cisco IOS XE" if "ios xe" in f"{field} {value}".lower() else "Network OS"
        if field and field.lower() not in {"product", "required_version", "version", "component"}:
            return field
        return str(value) if value and not re.match(r"^v?\d", str(value), flags=re.IGNORECASE) else None

    def _component_family(self, value: Any) -> str | None:
        text = str(value or "")
        match = re.search(r"(E\d-\d{4}\s*V\d)", text, flags=re.IGNORECASE)
        return match.group(1).upper().replace("V", " V") if match else None

    def _requirement_kind(self, operator: str) -> str:
        if operator == ">=":
            return "min_version"
        if operator in {"<", "<="}:
            return "max_version"
        if operator == "==":
            return "exact_version"
        if operator in {"!=", "not_in"}:
            return "not_allowed"
        if operator == "not_supported":
            return "not_supported"
        return "required_present"

    def _confidence(self, value: float | None) -> float:
        if value is None:
            return 0.5
        return max(0.0, min(float(value), 1.0))

    def _has_ambiguous_values(self, conditions: list[dict], requirements: list[dict]) -> bool:
        items = conditions + requirements
        return any(item["component_type"] == "unknown" or item["operator"] == "installed" and not item.get("value_raw") for item in items)

    def _has_uncertain_values(self, conditions: list[dict], requirements: list[dict]) -> bool:
        return any(item.get("version_scheme") == "cisco_ios_xe_unknown" for item in conditions + requirements)

    def _source_text(self, candidate: RuleCandidate, payload: dict) -> str:
        return " ".join(
            str(part)
            for part in [
                candidate.source_excerpt,
                getattr(candidate.source_chunk, "text", None),
                payload.get("rule_type"),
            ]
            if part
        )

    def _candidate_kind(self, payload: dict, rule_type: str, source_text: str) -> str:
        raw_kind = str(payload.get("candidate_kind") or "").lower()
        if raw_kind in CANDIDATE_KINDS:
            return raw_kind
        text = source_text.lower()
        if rule_type in {"model_support_min_version", "network_module_support_min_version", "license_support_fact", "software_image_fact", "rommon_version_fact"}:
            return "support_matrix_fact"
        if rule_type == "unsupported_feature" or "not supported" in text:
            return "unsupported_feature"
        if rule_type == "known_limitation" or "limitation" in text:
            return "known_limitation"
        if rule_type == "operational_warning" or any(term in text for term in ["do not", "must not", "warning", "power cycle"]):
            return "operational_warning"
        if rule_type == "not_a_rule":
            return "not_a_rule"
        if any(term in text for term in ["copyright", "table of contents", "document history"]):
            return "not_a_rule"
        return "compliance_rule"

    def _source_page(self, candidate: RuleCandidate, payload: dict) -> int | None:
        chunk_page = getattr(candidate.source_chunk, "page_number", None)
        return chunk_page if chunk_page is not None else payload.get("source_page")

    def _tags(self, payload: dict, candidate_kind: str) -> list[str]:
        tags = list(payload.get("tags") or [])
        if candidate_kind == "support_matrix_fact":
            tags.extend(["cisco", "support_matrix", "ios_xe"])
        return sorted(set(tags))

    def _model_value(self, item: dict, value: Any, component_name: Any) -> str | None:
        for candidate in [value, item.get("value_raw"), item.get("component_name"), component_name]:
            text = str(candidate or "").strip()
            if is_cisco_switch_model(text) or is_cisco_network_module(text):
                return text
        return None

    def _public_candidate_id(self, candidate_id: int) -> str:
        return f"RCAND-{candidate_id:06d}"

    def _public_chunk_id(self, chunk_id: int) -> str:
        return f"CHUNK-{chunk_id:06d}"

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
