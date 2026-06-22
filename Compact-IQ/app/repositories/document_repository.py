from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_document(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self.db.get(Document, document_id)

    def list_documents(self) -> list[Document]:
        statement = select(Document).order_by(Document.uploaded_at.desc())
        return list(self.db.scalars(statement).all())

    def update_document_status(self, document_id: str, status: str) -> Document | None:
        document = self.get_document(document_id)
        if document is None:
            return None

        document.status = status
        self.db.commit()
        self.db.refresh(document)
        return document
