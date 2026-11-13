import logging
from pathlib import Path

from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError

from backend.app.models.processing_job import ProcessingJob
from backend.app.schemas.meeting_analysis import MeetingRecord
from backend.app.schemas.transcription import (
    TranscriptSegment,
    TranscriptionResult,
)
from backend.app.services.audio_extractor import extract_audio
from backend.app.services.file_storage import UPLOAD_DIRECTORY
from backend.app.services.meeting_analyzer import analyze_transcript
from backend.app.services.meeting_repository import save_meeting
from backend.app.services.playback_audio import (
    create_playback_audio,
    get_playback_path,
)
from backend.app.services.processing_job_repository import (
    claim_analysis_retry,
    get_processing_job,
    update_processing_job,
)
from backend.app.services.speaker_diarization import diarize_transcript
from backend.app.services.transcription import transcribe_audio


logger = logging.getLogger(__name__)

AnalysisInput = tuple[TranscriptionResult, list[TranscriptSegment]]


def remove_processing_file(path: Path | None) -> None:
    if path is None:
        return

    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning(
            "Could not remove processing file %s",
            path,
            exc_info=True,
        )


async def process_meeting_job(job_id: int) -> MeetingRecord:
    job = await get_processing_job(job_id)
    return await _process_meeting_job(job)


async def retry_meeting_analysis(job_id: int) -> MeetingRecord:
    job = await get_processing_job(job_id)
    if (
        job.status != "failed"
        or job.stage != "analyzing"
        or job.meeting_id is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Only a job that failed during analysis can be retried.",
        )

    checkpoint = job.checkpoint or {}
    try:
        transcription = TranscriptionResult.model_validate(
            checkpoint.get("transcription"),
        )
        speaker_segments = TypeAdapter(list[TranscriptSegment]).validate_python(
            checkpoint.get("speaker_segments"),
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=409,
            detail="The saved transcript or speaker labels are unavailable.",
        ) from error

    if not (UPLOAD_DIRECTORY / job.stored_filename).is_file():
        raise HTTPException(
            status_code=409,
            detail="The original recording is missing. Upload it again to continue.",
        )

    await claim_analysis_retry(job.id, job.retry_count)
    return await _process_meeting_job(job, (transcription, speaker_segments))


async def _process_meeting_job(
    job: ProcessingJob,
    saved_analysis_input: AnalysisInput | None = None,
) -> MeetingRecord:
    uploaded_path = UPLOAD_DIRECTORY / job.stored_filename
    audio_path: Path | None = None
    temporary_playback_path: Path | None = None
    processing_succeeded = False
    stage = "analyzing" if saved_analysis_input is not None else "extracting"

    try:
        if saved_analysis_input is not None:
            transcription_result, speaker_segments = saved_analysis_input
        else:
            await update_processing_job(
                job.id,
                status="processing",
                stage=stage,
            )
            audio_path = await extract_audio(uploaded_path)

            stage = "transcribing"
            await update_processing_job(
                job.id,
                status="processing",
                stage=stage,
            )
            transcription_result = await transcribe_audio(audio_path)

            stage = "diarizing"
            await update_processing_job(
                job.id,
                status="processing",
                stage=stage,
                checkpoint={
                    "transcription": transcription_result.model_dump(mode="json"),
                },
            )
            speaker_segments = await diarize_transcript(
                audio_path,
                transcription_result.segments,
            )

            stage = "analyzing"
            await update_processing_job(
                job.id,
                status="processing",
                stage=stage,
                checkpoint={
                    "speaker_segments": [
                        segment.model_dump(mode="json")
                        for segment in speaker_segments
                    ],
                },
            )

        meeting_analysis = await analyze_transcript(
            transcription_result.transcript,
        )

        stage = "saving"
        await update_processing_job(
            job.id,
            status="processing",
            stage=stage,
            checkpoint={
                "analysis": meeting_analysis.model_dump(mode="json"),
            },
        )

        temporary_playback_path = await create_playback_audio(
            audio_path or uploaded_path,
            uploaded_path.stem,
        )

        saved_meeting = await save_meeting(
            original_filename=job.original_filename,
            content_type=job.content_type,
            size_bytes=job.size_bytes,
            transcript=transcription_result.transcript,
            language=transcription_result.language,
            language_probability=(
                transcription_result.language_probability
            ),
            duration_seconds=transcription_result.duration_seconds,
            segments=speaker_segments,
            analysis=meeting_analysis,
            processing_job_id=job.id,
        )

        temporary_playback_path.replace(
            get_playback_path(saved_meeting.id),
        )
        result = MeetingRecord.model_validate(saved_meeting)

        await update_processing_job(
            job.id,
            status="completed",
            stage="completed",
        )

        processing_succeeded = True
        return result

    except Exception as error:
        logger.exception(
            "Processing job %s failed during %s",
            job.id,
            stage,
        )

        message = (
            error.detail
            if isinstance(error, HTTPException)
            and isinstance(error.detail, str)
            else "The meeting could not be processed."
        )

        try:
            await update_processing_job(
                job.id,
                status="failed",
                stage=stage,
                error_message=message,
            )
        except Exception:
            logger.exception(
                "Could not record failure for job %s",
                job.id,
            )

        headers = (
            dict(error.headers or {})
            if isinstance(error, HTTPException)
            else {}
        )
        headers["X-Processing-Job-ID"] = str(job.id)

        raise HTTPException(
            status_code=(
                error.status_code
                if isinstance(error, HTTPException)
                else 500
            ),
            detail=message,
            headers=headers,
        ) from error

    finally:
        remove_processing_file(audio_path)
        remove_processing_file(temporary_playback_path)

        if processing_succeeded:
            remove_processing_file(uploaded_path)
