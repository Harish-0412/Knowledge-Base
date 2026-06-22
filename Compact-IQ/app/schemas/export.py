from pydantic import BaseModel


class RuleCandidateExportResponse(BaseModel):
    document_id: str
    export_type: str
    rule_candidates: list[dict]
