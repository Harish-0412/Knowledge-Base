from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document
from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.debug import LLMTestRequest, LLMTestResponse
from app.schemas.pipeline import DocIntelPipelineResponse
from app.services.llm_service import LLMServiceFactory
from app.services.pipeline_service import DocIntelPipelineService

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.post("/llm-test", response_model=LLMTestResponse)
def llm_test(request: LLMTestRequest) -> dict:
    settings = get_settings()
    service = LLMServiceFactory.create(settings)
    result = service.generate_json(request.prompt)
    return {
        "provider": service.provider,
        "model": settings.ollama_model,
        "ok": True,
        "result": result,
    }


@router.post("/run-demo-document", response_model=DocIntelPipelineResponse)
def run_demo_document(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    repository = DocumentRepository(db)
    for document in repository.list_documents():
        if document.original_filename == "mock_release_notes.txt":
            return DocIntelPipelineService(db).run(document.document_id)

    example_path = Path("examples/mock_release_notes.txt")
    if example_path.exists():
        content = example_path.read_bytes()
    else:
        content = b"Windows Server 2012 requires BIOS 1.3.5 or later."

    document_id = f"DOC-{uuid4().hex[:12].upper()}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{document_id}.txt"
    stored_path = upload_dir / stored_filename
    stored_path.write_bytes(content)

    document = Document(
        document_id=document_id,
        filename=stored_filename,
        original_filename="mock_release_notes.txt",
        file_path=str(stored_path),
        content_type="text/plain",
        source_type="text",
        file_size_bytes=len(content),
        status="uploaded",
        metadata_json={"created_by": "debug.run-demo-document"},
    )
    repository.create_document(document)
    return DocIntelPipelineService(db).run(document_id)
