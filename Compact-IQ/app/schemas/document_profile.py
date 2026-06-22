from pydantic import BaseModel, ConfigDict, Field


class DocumentProfileItem(BaseModel):
    page_number: int
    page_type: str
    recommended_extractor: str
    confidence: float
    reason: str
    signals_json: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DocumentProfileResponse(BaseModel):
    document_id: str
    profiles: list[DocumentProfileItem]
