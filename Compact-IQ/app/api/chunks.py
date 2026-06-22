from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorResponse
from app.db.models import DocumentChunk
from app.db.session import get_db
from app.repositories.chunk_repository import ChunkRepository
from app.schemas.document_chunk import DocumentChunkResponse

router = APIRouter(prefix="/chunks", tags=["Chunks"], responses={404: {"model": ErrorResponse}})


@router.get("/{chunk_id}", response_model=DocumentChunkResponse)
def get_chunk(chunk_id: int, db: Session = Depends(get_db)) -> DocumentChunk:
    chunk = ChunkRepository(db).get_chunk(chunk_id)
    if chunk is None:
        raise AppError(
            code="chunk_not_found",
            message="Document chunk was not found.",
            status_code=404,
            details={"chunk_id": chunk_id},
        )
    return chunk
