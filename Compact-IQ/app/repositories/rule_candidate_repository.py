from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RuleCandidate


class RuleCandidateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_rule_candidate(self, candidate: RuleCandidate) -> RuleCandidate:
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def create_many(self, candidates: list[RuleCandidate]) -> list[RuleCandidate]:
        self.db.add_all(candidates)
        self.db.commit()
        for candidate in candidates:
            self.db.refresh(candidate)
        return candidates

    def list_by_document(self, document_id: str) -> list[RuleCandidate]:
        statement = (
            select(RuleCandidate)
            .where(RuleCandidate.document_id == document_id)
            .order_by(RuleCandidate.created_at.desc(), RuleCandidate.candidate_id.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_all(self) -> list[RuleCandidate]:
        statement = select(RuleCandidate).order_by(RuleCandidate.created_at.desc(), RuleCandidate.candidate_id.desc())
        return list(self.db.scalars(statement).all())

    def get_by_id(self, candidate_id: int) -> RuleCandidate | None:
        return self.db.get(RuleCandidate, candidate_id)

    def save(self, candidate: RuleCandidate) -> RuleCandidate:
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def bulk_update_review_status(self, updates: list[dict]) -> list[RuleCandidate]:
        """Atomically apply review-status updates for multiple candidates.

        Each dict in ``updates`` must have ``candidate_id`` (int) and
        ``review_status`` (str). Optional keys: ``tier``, ``auto_approved``,
        ``rejection_reason`` — these are merged into ``metadata_json``.
        Returns the list of updated candidates (only those found in DB).
        """
        updated: list[RuleCandidate] = []
        for item in updates:
            candidate = self.db.get(RuleCandidate, item["candidate_id"])
            if candidate is None:
                continue
            candidate.review_status = item["review_status"]
            # Merge optional review metadata into the JSON column
            meta = dict(candidate.metadata_json or {})
            if "tier" in item:
                meta["review_tier"] = item["tier"]
            if "auto_approved" in item:
                meta["auto_approved"] = item["auto_approved"]
            if "rejection_reason" in item:
                meta["rejection_reason"] = item["rejection_reason"]
            meta["reviewed_at"] = datetime.now(UTC).isoformat()
            candidate.metadata_json = meta
            updated.append(candidate)
        if updated:
            self.db.commit()
            for c in updated:
                self.db.refresh(c)
        return updated
