import asyncio

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models.processing_job import ProcessingJob


def create_processing_job_sync(
    *,
    original_filename: str,
    stored_filename: str,
    content_type: str | None,
    size_bytes: int,
) -> ProcessingJob:
    try:
        with SessionLocal() as session:
            job = ProcessingJob(
                original_filename=original_filename,
                stored_filename=stored_filename,
                content_type=content_type,
                size_bytes=size_bytes,
                status="queued",
                stage="uploaded",
            )

            session.add(job)
            session.commit()
            session.refresh(job)

            return job

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="The processing job could not be saved.",
        ) from error


async def create_processing_job(
    *,
    original_filename: str,
    stored_filename: str,
    content_type: str | None,
    size_bytes: int,
) -> ProcessingJob:
    return await asyncio.to_thread(
        create_processing_job_sync,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )


def get_processing_job_sync(job_id: int) -> ProcessingJob:
    try:
        with SessionLocal() as session:
            job = session.get(ProcessingJob, job_id)

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="The processing job could not be loaded.",
        ) from error

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found.",
        )

    return job


async def get_processing_job(job_id: int) -> ProcessingJob:
    return await asyncio.to_thread(
        get_processing_job_sync,
        job_id,
    )
    
def update_processing_job_sync(
    job_id: int,
    *,
    status: str,
    stage: str,
    checkpoint: dict[str, object] | None = None,
    error_message: str | None = None,
) -> ProcessingJob:
    allowed_statuses = {
        "queued",
        "processing",
        "failed",
        "interrupted",
        "completed",
    }

    allowed_stages = {
        "uploaded",
        "extracting",
        "transcribing",
        "diarizing",
        "analyzing",
        "saving",
        "completed",
    }

    if status not in allowed_statuses:
        raise ValueError(f"Invalid job status: {status}")

    if stage not in allowed_stages:
        raise ValueError(f"Invalid processing stage: {stage}")

    try:
        with SessionLocal() as session:
            job = session.get(ProcessingJob, job_id)

            if job is None:
                raise HTTPException(
                    status_code=404,
                    detail="Processing job not found.",
                )

            job.status = status
            job.stage = stage
            job.error_message = error_message

            if checkpoint is not None:
                saved_checkpoint = dict(job.checkpoint or {})
                saved_checkpoint.update(checkpoint)
                job.checkpoint = saved_checkpoint

            session.commit()
            session.refresh(job)

            return job

    except HTTPException:
        try:
            with SessionLocal() as session:
                session.rollback()
        except Exception:
            pass
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="The processing job could not be updated.",
        ) from error

async def update_processing_job(
    job_id: int,
    *,
    status: str,
    stage: str,
    checkpoint: dict[str, object] | None = None,
    error_message: str | None = None,
) -> ProcessingJob:
    return await asyncio.to_thread(
        update_processing_job_sync,
        job_id,
        status=status,
        stage=stage,
        checkpoint=checkpoint,
        error_message=error_message,
    )