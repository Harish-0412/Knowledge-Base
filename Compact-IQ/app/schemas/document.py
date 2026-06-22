from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    original_filename: str
    source_type: str
    status: str
    file_size_bytes: int

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(DocumentUploadResponse):
    file_path: str
    content_type: str | None
    display_name: str
    file_type: str
    uploaded_at: datetime
    updated_at: datetime
    metadata_json: dict

    model_config = ConfigDict(from_attributes=True)
