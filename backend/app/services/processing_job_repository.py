import asyncio

from fastapi import HTTPException
from sqlalchemy import update
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


def claim_analysis_retry_sync(job_id: int, retry_count: int) -> None:
    # Check the old state and claim the retry in one database write.
    statement = (
        update(ProcessingJob)
        .where(
            ProcessingJob.id == job_id,
            ProcessingJob.status == "failed",
            ProcessingJob.stage == "analyzing",
            ProcessingJob.meeting_id.is_(None),
            ProcessingJob.retry_count == retry_count,
        )
        .values(
            status="processing",
            error_message=None,
            retry_count=ProcessingJob.retry_count + 1,
        )
    )

    try:
        with SessionLocal() as session:
            result = session.execute(statement)
            if result.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail="This job is no longer available to retry.",
                )
            session.commit()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="The retry could not be started.",
        ) from error


async def claim_analysis_retry(job_id: int, retry_count: int) -> None:
    await asyncio.to_thread(claim_analysis_retry_sync, job_id, retry_count)


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
