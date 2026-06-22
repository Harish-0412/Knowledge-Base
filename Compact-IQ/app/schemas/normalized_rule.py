from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ComponentType = Literal[
    "bios",
    "cpu",
    "os",
    "firmware",
    "driver",
    "agent",
    "management_tool",
    "hba",
    "raid_controller",
    "network_adapter",
    "storage_controller",
    "virtualization_feature",
    "tpm",
    "model",
    "device_type",
    "hardware_revision",
    "readiness",
    "device",
    "device_family",
    "device_model",
    "network_module",
    "network_os",
    "software_image",
    "bootloader",
    "license",
    "feature",
    "transceiver",
    "upgrade_process",
    "storage",
    "unknown",
]

Operator = Literal["installed", "exists", "not_exists", "==", "!=", ">=", "<=", ">", "<", "matches", "in", "not_in", "not_supported", "must_not"]
RuleType = Literal[
    "min_version_constraint",
    "max_version_constraint",
    "exact_version_constraint",
    "incompatible_combination",
    "feature_support_added",
    "known_issue_fixed",
    "deprecated_after",
    "update_order_constraint",
    "readiness_requirement",
    "model_support_min_version",
    "network_module_support_min_version",
    "license_support_fact",
    "software_image_fact",
    "rommon_version_fact",
    "unsupported_feature",
    "configuration_requirement",
    "upgrade_order_constraint",
    "operational_warning",
    "known_limitation",
    "not_a_rule",
]
Severity = Literal["info", "warning", "critical", "blocker"]
ReviewStatus = Literal["pending_review", "approved", "edited", "rejected", "needs_clarification"]
CandidateKind = Literal[
    "support_matrix_fact",
    "compliance_rule",
    "unsupported_feature",
    "known_limitation",
    "operational_warning",
    "informational_note",
    "not_a_rule",
]


class NormalizedCondition(BaseModel):
    condition_id: str
    component_type: ComponentType
    operator: Operator
    component_name: str | None = None
    component_family: str | None = None
    vendor: str | None = None
    value_raw: str | int | float | bool | None = None
    value_normalized: str | int | float | bool | None = None
    version_raw: str | None = None
    version_normalized: str | None = None
    version_scheme: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class NormalizedRequirement(BaseModel):
    requirement_id: str
    component_type: ComponentType
    operator: Operator
    requirement_kind: Literal[
        "min_version",
        "max_version",
        "exact_version",
        "not_allowed",
        "required_present",
        "not_supported",
        "update_before",
        "readiness",
    ]
    component_name: str | None = None
    component_family: str | None = None
    value_raw: str | int | float | bool | None = None
    value_normalized: str | int | float | bool | None = None
    version_raw: str | None = None
    version_normalized: str | None = None
    version_scheme: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class NormalizedRuleCandidate(BaseModel):
    candidate_id: str
    source_document_id: str = Field(pattern=r"^DOC-[A-F0-9]{12}$")
    source_chunk_id: str
    source_page: int | None = None
    source_excerpt: str
    candidate_kind: CandidateKind = "compliance_rule"
    rule_type: RuleType
    condition_logic: Literal["AND", "OR"]
    conditions: list[NormalizedCondition]
    requirements: list[NormalizedRequirement]
    exceptions: list[NormalizedCondition] = Field(default_factory=list)
    severity: Severity
    confidence_score: float = Field(ge=0, le=1)
    confidence_reason: str | None = None
    review_status: ReviewStatus
    remediation_hint: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
