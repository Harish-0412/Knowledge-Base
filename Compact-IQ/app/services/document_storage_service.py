import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings, get_settings
from app.core.errors import AppError


SOURCE_TYPE_BY_EXTENSION = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
    ".csv": "csv",
    ".docx": "docx",
}


class StoredDocument:
    def __init__(
        self,
        document_id: str,
        filename: str,
        original_filename: str,
        file_path: str,
        content_type: str | None,
        source_type: str,
        file_size_bytes: int,
    ) -> None:
        self.document_id = document_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.content_type = content_type
        self.source_type = source_type
        self.file_size_bytes = file_size_bytes


class DocumentStorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def save_upload(self, upload: UploadFile) -> StoredDocument:
        original_filename = self._clean_filename(upload.filename)
        extension = Path(original_filename).suffix.lower()
        source_type = SOURCE_TYPE_BY_EXTENSION.get(extension)

        if source_type is None:
            raise AppError(
                code="unsupported_file_type",
                message="Unsupported file type. Accepted types are .pdf, .txt, .md, .csv, and .docx.",
                status_code=400,
                details={"filename": original_filename},
            )

        content = await upload.read()
        file_size_bytes = len(content)
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if file_size_bytes > max_bytes:
            raise AppError(
                code="file_too_large",
                message=f"Uploaded file exceeds the {self.settings.max_upload_mb} MB limit.",
                status_code=413,
                details={"file_size_bytes": file_size_bytes, "max_upload_mb": self.settings.max_upload_mb},
            )

        document_id = f"DOC-{uuid4().hex[:12].upper()}"
        stored_filename = f"{document_id}{extension}"
        upload_dir = Path(self.settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = upload_dir / stored_filename
        stored_path.write_bytes(content)

        return StoredDocument(
            document_id=document_id,
            filename=stored_filename,
            original_filename=original_filename,
            file_path=str(stored_path),
            content_type=upload.content_type,
            source_type=source_type,
            file_size_bytes=file_size_bytes,
        )

    def _clean_filename(self, filename: str | None) -> str:
        if not filename:
            raise AppError(
                code="missing_filename",
                message="Uploaded file must include a filename.",
                status_code=400,
            )

        cleaned = Path(filename).name
        cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", cleaned).strip()
        if not cleaned:
            raise AppError(
                code="invalid_filename",
                message="Uploaded filename is invalid.",
                status_code=400,
            )
        return cleaned
