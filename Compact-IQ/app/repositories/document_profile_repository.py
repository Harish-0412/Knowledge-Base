from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import DocumentProfile


class DocumentProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_profiles(self, document_id: str, profiles: list[DocumentProfile]) -> list[DocumentProfile]:
        self.db.execute(delete(DocumentProfile).where(DocumentProfile.document_id == document_id))
        self.db.add_all(profiles)
        self.db.commit()
        for profile in profiles:
            self.db.refresh(profile)
        return profiles

    def list_profiles(self, document_id: str) -> list[DocumentProfile]:
        statement = (
            select(DocumentProfile)
            .where(DocumentProfile.document_id == document_id)
            .order_by(DocumentProfile.page_number.asc(), DocumentProfile.profile_id.asc())
        )
        return list(self.db.scalars(statement).all())
