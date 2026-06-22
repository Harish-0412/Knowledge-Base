from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LLMComponentType = Literal[
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
    "hardware_revision",
    "readiness",
    "unknown",
]

LLMOperator = Literal[
    "installed",
    "exists",
    "not_exists",
    "==",
    "!=",
    ">=",
    "<=",
    ">",
    "<",
    "matches",
    "in",
    "not_in",
    "not_supported",
    "must_not",
]
LLMRuleType = Literal[
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
LLMSeverity = Literal["info", "warning", "critical", "blocker"]
LLMCandidateKind = Literal[
    "support_matrix_fact",
    "compliance_rule",
    "unsupported_feature",
    "known_limitation",
    "operational_warning",
    "informational_note",
    "not_a_rule",
]
LLMRequirementKind = Literal[
    "min_version",
    "max_version",
    "exact_version",
    "not_allowed",
    "not_supported",
    "required_present",
    "update_before",
    "readiness",
]


class LLMComponentValue(BaseModel):
    component_type: LLMComponentType
    operator: LLMOperator
    component_name: str | None = None
    component_family: str | None = None
    vendor: str | None = None
    value_raw: str | int | float | bool | None = None
    version_raw: str | None = None
    version_scheme: str | None = None

    model_config = ConfigDict(extra="forbid")


class LLMRequirementValue(LLMComponentValue):
    requirement_kind: LLMRequirementKind


class LLMRuleCandidate(BaseModel):
    candidate_kind: LLMCandidateKind | None = None
    rule_type: LLMRuleType
    condition_logic: Literal["AND", "OR"]
    conditions: list[LLMComponentValue] = Field(default_factory=list)
    requirements: list[LLMRequirementValue] = Field(default_factory=list)
    exceptions: list[LLMComponentValue] = Field(default_factory=list)
    severity: LLMSeverity
    confidence_score: float = Field(ge=0, le=1)
    confidence_reason: str | None = None
    remediation_hint: str | None = None

    model_config = ConfigDict(extra="forbid")


class LLMExtractionResponse(BaseModel):
    rule_candidates: list[LLMRuleCandidate] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
