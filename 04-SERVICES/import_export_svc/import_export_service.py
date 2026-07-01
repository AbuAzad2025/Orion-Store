from __future__ import annotations

from core.exceptions import NotFoundError
from import_export.import_export import ImportExportJob
from orion.extensions import db


class ImportExportService:
    def create_job(self, *, tenant_id: int, job_type: str, entity_type: str, file_url: str | None = None, user_id: int | None = None) -> ImportExportJob:
        job = ImportExportJob(tenant_id=tenant_id, job_type=job_type, entity_type=entity_type, file_url=file_url, user_id=user_id)
        db.session.add(job)
        db.session.commit()
        return job

    def list_jobs(self, tenant_id: int) -> list[ImportExportJob]:
        return ImportExportJob.query.filter_by(tenant_id=tenant_id).order_by(ImportExportJob.created_at.desc()).all()

    def update_progress(self, *, job_id: int, tenant_id: int, processed: int = 0, failed: int = 0, total: int = 0) -> ImportExportJob:
        job = ImportExportJob.query.filter_by(id=job_id, tenant_id=tenant_id).first()
        if not job:
            raise NotFoundError("Job not found.")
        job.processed_count = processed
        job.failed_count = failed
        job.total_count = total
        if processed + failed >= total:
            job.status = "completed" if failed == 0 else "completed_with_errors"
        db.session.commit()
        return job
