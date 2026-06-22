from pydantic import BaseModel


class LocalExportFileStatus(BaseModel):
    path: str
    exists: bool


class DocumentExportsResponse(BaseModel):
    document_id: str
    exports: dict[str, LocalExportFileStatus]
