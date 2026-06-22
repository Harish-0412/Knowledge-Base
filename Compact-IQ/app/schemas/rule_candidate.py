from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RuleCandidateResponse(BaseModel):
    candidate_id: int
    document_id: str
    source_chunk_id: int
    rule_id: str | None
    rule_type: str | None
    condition_logic: str | None
    conditions_json: dict | list | None
    requirement_json: dict | list | None
    severity: str | None
    confidence_score: float | None
    confidence_reason: str | None
    explanation: str | None
    source_excerpt: str
    review_status: str
    normalization_status: str
    raw_llm_output_json: dict | list
    normalized_rule_json: dict | list | None
    validation_errors_json: dict | list | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleCandidateListResponse(BaseModel):
    document_id: str
    rule_candidates: list[RuleCandidateResponse]


class RuleCandidateReviewRequest(BaseModel):
    review_status: str
    reviewed_by: str | None = None
    edited_rule: dict | None = None
    notes: str | None = None
    # Tiered review fields (additive — do not break existing contract)
    tier: str | None = None             # "auto" | "batch" | "individual"
    auto_approved: bool | None = None
    rejection_reason: str | None = None


class RuleCandidateReviewResponse(BaseModel):
    candidate_id: int
    review_status: str
    message: str
    is_temporary_review_flow: bool = True
    tier: str | None = None
    rejection_reason: str | None = None


class RuleExtractionResponse(BaseModel):
    document_id: str
    rule_candidates_created: int
    raw_rule_candidates_created: int = 0
    normalized_rule_candidates_created: int = 0
    normalization_status: str
    candidate_quality: dict = {}
    quality_warning_count: int = 0
    pipeline_stage: str | None = None
    pipeline_mode: str = "legacy"
    total_objects: int = 0
    processing_lane_summary: dict = {}
    llm_call_count: int = 0
    deterministic_candidate_count: int = 0
    llm_candidate_count: int = 0
    exports: dict = {}
    warnings: list[str]
