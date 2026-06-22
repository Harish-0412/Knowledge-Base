from pydantic import BaseModel


class DocIntelPipelineResponse(BaseModel):
    document_id: str
    status: str
    profile_count: int
    extractors_used: list[str] = []
    chunks_created: int
    raw_rule_candidates_created: int = 0
    rule_candidates_created: int
    normalized_rule_candidates_created: int = 0
    normalized_candidates: int
    needs_human_review: int
    failed_candidates: int
    candidate_quality: dict = {}
    pipeline_mode: str = "legacy"
    total_objects: int = 0
    processing_lane_summary: dict = {}
    llm_call_count: int = 0
    deterministic_candidate_count: int = 0
    llm_candidate_count: int = 0
    exports: dict[str, str] = {}
    warnings: list[str]
