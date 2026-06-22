from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import ExtractionJob


class ExtractionJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running_job(self, document_id: str, job_type: str) -> ExtractionJob:
        job = ExtractionJob(
            document_id=document_id,
            job_type=job_type,
            status="running",
            started_at=datetime.now(UTC),
            metadata_json={},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_succeeded(self, job: ExtractionJob) -> ExtractionJob:
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_failed(self, job: ExtractionJob, error_message: str) -> ExtractionJob:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.error_message = error_message
        self.db.commit()
        self.db.refresh(job)
        return job
